import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.db import async_session_maker, init_db
from src.models import Campaign, CampaignContact, User, Voice
from src.redis_client import get_redis_pool
from src.services import campaign_dialer


@pytest.fixture(autouse=True)
async def _init_database():
    await init_db()
    # The status-update dedupe key is real Redis state that outlives a single
    # test process; without this, fake call_sids (which restart from "CAFAKE1"
    # in each test) collide with dedupe keys left over from earlier runs.
    await get_redis_pool().flushdb()


async def _make_campaign(email: str, n_contacts: int) -> int:
    async with async_session_maker() as session:
        user = User(first_name="C", last_name="T", email=email, password_hash="x")
        session.add(user)
        await session.flush()
        session.add(Voice(user_id=user.id, voice_id="v1"))
        campaign = Campaign(
            user_id=user.id,
            campaign_name="Test",
            agent_name="Sara",
            greeting_message="hi",
            role_of_bot="sales",
            company_name="Acme",
        )
        session.add(campaign)
        await session.flush()
        for i in range(n_contacts):
            session.add(
                CampaignContact(campaign_id=campaign.id, first_name=f"C{i}", phone_e164=f"+1201555{i:04d}")
            )
        await session.commit()
        return campaign.id


async def _fake_call_factory():
    # Globally unique per call (like real Twilio SIDs) — the test DB persists
    # across tests in this session, so reused SIDs would collide with rows
    # from earlier tests and match the wrong contact.
    async def fake_place_outbound_call(**kwargs):
        return f"CAFAKE{uuid.uuid4().hex}"

    return fake_place_outbound_call


async def test_dial_respects_max_concurrent_calls():
    campaign_id = await _make_campaign("dialer1@example.com", 4)
    fake_call = await _fake_call_factory()

    with patch("src.services.campaign_dialer.place_outbound_call", side_effect=fake_call):
        with patch("src.services.campaign_dialer.get_settings") as mock_settings:
            mock_settings.return_value.max_concurrent_calls = 2
            results = [await campaign_dialer.dial_next_for_campaign(campaign_id) for _ in range(4)]

    async with async_session_maker() as session:
        contacts = (
            await session.scalars(
                select(CampaignContact).where(CampaignContact.campaign_id == campaign_id).order_by(CampaignContact.id)
            )
        ).all()

    dialing = [c for c in contacts if c.status == "dialing"]
    pending = [c for c in contacts if c.status == "pending"]
    assert len(dialing) == 2
    assert len(pending) == 2
    assert results == [True, True, False, False]


async def test_completion_dials_next_pending_contact():
    campaign_id = await _make_campaign("dialer2@example.com", 2)
    fake_call = await _fake_call_factory()

    with patch("src.services.campaign_dialer.place_outbound_call", side_effect=fake_call):
        with patch("src.services.campaign_dialer.get_settings") as mock_settings:
            mock_settings.return_value.max_concurrent_calls = 1
            await campaign_dialer.dial_next_for_campaign(campaign_id)

            async with async_session_maker() as session:
                contacts = (
                    await session.scalars(
                        select(CampaignContact)
                        .where(CampaignContact.campaign_id == campaign_id)
                        .order_by(CampaignContact.id)
                    )
                ).all()
            assert contacts[0].status == "dialing"
            assert contacts[1].status == "pending"

            await campaign_dialer.handle_call_status_update(contacts[0].call_sid, "completed")

            async with async_session_maker() as session:
                contacts = (
                    await session.scalars(
                        select(CampaignContact)
                        .where(CampaignContact.campaign_id == campaign_id)
                        .order_by(CampaignContact.id)
                    )
                ).all()
            assert contacts[0].status == "completed"
            assert contacts[1].status == "dialing"  # freed capacity picked up automatically


async def test_duplicate_status_callback_is_deduped():
    campaign_id = await _make_campaign("dialer3@example.com", 1)
    fake_call = await _fake_call_factory()

    with patch("src.services.campaign_dialer.place_outbound_call", side_effect=fake_call):
        with patch("src.services.campaign_dialer.get_settings") as mock_settings:
            mock_settings.return_value.max_concurrent_calls = 1
            await campaign_dialer.dial_next_for_campaign(campaign_id)

        async with async_session_maker() as session:
            contact = await session.scalar(
                select(CampaignContact).where(CampaignContact.campaign_id == campaign_id)
            )
            call_sid = contact.call_sid

        await campaign_dialer.handle_call_status_update(call_sid, "completed")
        await campaign_dialer.handle_call_status_update(call_sid, "completed")  # Twilio retry

        async with async_session_maker() as session:
            contact = await session.scalar(
                select(CampaignContact).where(CampaignContact.campaign_id == campaign_id)
            )
            assert contact.status == "completed"
            assert contact.attempt_count == 1  # not re-dialed by the duplicate callback
