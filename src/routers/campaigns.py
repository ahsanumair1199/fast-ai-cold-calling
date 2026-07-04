from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Campaign, CampaignContact, User
from ..schemas.campaign import CampaignOut, ContactOut
from ..services.auth_service import get_current_user
from ..services.campaign_service import create_campaign_with_contacts, parse_contact_excel

campaigns_router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@campaigns_router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    campaign_name: str = Form(...),
    agent_name: str = Form(...),
    greeting_message: str = Form(...),
    role_of_bot: str = Form(...),
    company_name: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    contacts, errors = await parse_contact_excel(file)
    campaign = await create_campaign_with_contacts(
        session,
        user_id=user.id,
        campaign_name=campaign_name,
        agent_name=agent_name,
        greeting_message=greeting_message,
        role_of_bot=role_of_bot,
        company_name=company_name,
        contacts=contacts,
    )
    return CampaignOut(
        id=campaign.id,
        campaign_name=campaign.campaign_name,
        contact_count=len(contacts),
        skipped_rows=errors,
    )


@campaigns_router.get("/{campaign_id}/contacts", response_model=list[ContactOut])
async def list_campaign_contacts(
    campaign_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None or campaign.user_id != user.id:
        raise HTTPException(status_code=404, detail="Campaign not found")

    contacts = await session.scalars(
        select(CampaignContact).where(CampaignContact.campaign_id == campaign_id)
    )
    return list(contacts)
