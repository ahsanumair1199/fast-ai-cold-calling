import asyncio
import logging
import uuid

from sqlalchemy import func, select, update

from ..config import get_settings
from ..core.call_session import PersonaConfig
from ..db import async_session_maker
from ..models import Campaign, CampaignContact, ContactStatus
from ..redis_client import get_redis_pool
from .call_service import place_outbound_call
from .voice_service import get_user_voice_id

logger = logging.getLogger(__name__)

LEADER_LOCK_KEY = "campaign_dialer:leader"
LEADER_LOCK_TTL_SECONDS = 30
POLL_INTERVAL_SECONDS = 5
_INSTANCE_ID = uuid.uuid4().hex


async def _try_hold_leader_lock() -> bool:
    """SETNX-based leader election so only one process dials at a time even if
    this app is later scaled to multiple replicas — safe to run this loop
    everywhere, only the current leader actually does anything."""
    redis = get_redis_pool()
    acquired = await redis.set(LEADER_LOCK_KEY, _INSTANCE_ID, nx=True, ex=LEADER_LOCK_TTL_SECONDS)
    if acquired:
        return True
    current = await redis.get(LEADER_LOCK_KEY)
    if current == _INSTANCE_ID:
        await redis.expire(LEADER_LOCK_KEY, LEADER_LOCK_TTL_SECONDS)
        return True
    return False


async def _claim_next_pending_contact(session, campaign_id: int) -> CampaignContact | None:
    """Optimistic claim: works identically on SQLite and Postgres without
    dialect-specific locking syntax. The WHERE ... status='pending' guard means
    only one concurrent claimer's UPDATE can ever affect the row."""
    contact_id = await session.scalar(
        select(CampaignContact.id)
        .where(
            CampaignContact.campaign_id == campaign_id,
            CampaignContact.status == ContactStatus.PENDING.value,
        )
        .order_by(CampaignContact.id)
        .limit(1)
    )
    if contact_id is None:
        return None

    result = await session.execute(
        update(CampaignContact)
        .where(CampaignContact.id == contact_id, CampaignContact.status == ContactStatus.PENDING.value)
        .values(status=ContactStatus.DIALING.value, attempt_count=CampaignContact.attempt_count + 1)
    )
    if result.rowcount == 0:
        return None  # lost the race to another claimer
    await session.commit()
    return await session.get(CampaignContact, contact_id)


async def dial_next_for_campaign(campaign_id: int) -> bool:
    """Claims and dials the next pending contact for a campaign, if capacity
    allows. Called by the poll loop and directly by the status webhook when a
    call finishes, so the next contact goes out immediately rather than
    waiting for the next poll tick."""
    settings = get_settings()
    async with async_session_maker() as session:
        active_count = await session.scalar(
            select(func.count())
            .select_from(CampaignContact)
            .where(
                CampaignContact.campaign_id == campaign_id,
                CampaignContact.status == ContactStatus.DIALING.value,
            )
        )
        if active_count >= settings.max_concurrent_calls:
            return False

        contact = await _claim_next_pending_contact(session, campaign_id)
        if contact is None:
            return False

        campaign = await session.get(Campaign, campaign_id)
        persona = PersonaConfig(
            agent_name=campaign.agent_name,
            greeting_message=campaign.greeting_message,
            role_of_bot=campaign.role_of_bot,
            company_name=campaign.company_name,
            target_first_name=contact.first_name,
        )
        voice_id = await get_user_voice_id(session, campaign.user_id)

        try:
            call_sid = await place_outbound_call(
                user_id=campaign.user_id,
                phone_e164=contact.phone_e164,
                persona=persona,
                voice_id=voice_id,
            )
        except Exception:
            logger.exception("Failed to dial campaign contact %s", contact.id)
            contact.status = ContactStatus.FAILED.value
            await session.commit()
            return True

        contact.call_sid = call_sid
        await session.commit()
        return True


async def handle_call_status_update(call_sid: str, call_status: str) -> None:
    """The single, canonical trigger for campaign progression — replaces the old
    app's two independent triggers (SQLAlchemy after_insert signal + WS-close
    dequeue). Twilio retries status callbacks, so dedupe by (CallSid, CallStatus)."""
    redis = get_redis_pool()
    dedupe_key = f"status_seen:{call_sid}:{call_status}"
    first_seen = await redis.set(dedupe_key, "1", nx=True, ex=3600)
    if not first_seen:
        return

    async with async_session_maker() as session:
        contact = await session.scalar(select(CampaignContact).where(CampaignContact.call_sid == call_sid))
        if contact is None:
            return  # not a campaign call (e.g. an ad-hoc /calls/outbound call)
        contact.status = (
            ContactStatus.COMPLETED.value if call_status == "completed" else ContactStatus.FAILED.value
        )
        campaign_id = contact.campaign_id
        await session.commit()

    await dial_next_for_campaign(campaign_id)


async def run_dialer_loop() -> None:
    while True:
        try:
            if await _try_hold_leader_lock():
                await _poll_all_campaigns()
        except Exception:
            logger.exception("campaign dialer poll iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _poll_all_campaigns() -> None:
    async with async_session_maker() as session:
        campaign_ids = (
            await session.scalars(
                select(CampaignContact.campaign_id)
                .where(CampaignContact.status == ContactStatus.PENDING.value)
                .distinct()
            )
        ).all()
    for campaign_id in campaign_ids:
        await dial_next_for_campaign(campaign_id)
