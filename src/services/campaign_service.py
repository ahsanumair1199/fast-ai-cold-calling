import io

import openpyxl
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Campaign, CampaignContact
from ..utils.phone import to_e164

REQUIRED_COLUMNS = ["first_name", "phone"]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB — plenty for a contact list, bounds memory use


async def parse_contact_excel(file: UploadFile) -> tuple[list[dict], list[str]]:
    if file.filename and not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="File must be an .xlsx Excel workbook")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    try:
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read the uploaded file as an Excel workbook")

    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=422, detail="Excel file is empty")

    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required columns: {missing}")

    contacts: list[dict] = []
    errors: list[str] = []
    for i, row in enumerate(rows[1:], start=2):
        record = dict(zip(header, row))
        first_name = str(record.get("first_name") or "").strip()
        phone_raw = str(record.get("phone") or "").strip()
        if not first_name or not phone_raw:
            errors.append(f"Row {i}: missing first_name or phone")
            continue
        try:
            phone_e164 = to_e164(phone_raw)
        except HTTPException:
            errors.append(f"Row {i}: invalid phone number '{phone_raw}'")
            continue
        contacts.append({"first_name": first_name, "phone_e164": phone_e164})

    if not contacts:
        raise HTTPException(status_code=422, detail=f"No valid contacts found. Errors: {errors}")
    return contacts, errors


async def create_campaign_with_contacts(
    session: AsyncSession,
    *,
    user_id: int,
    campaign_name: str,
    agent_name: str,
    greeting_message: str,
    role_of_bot: str,
    company_name: str,
    contacts: list[dict],
) -> Campaign:
    campaign = Campaign(
        user_id=user_id,
        campaign_name=campaign_name,
        agent_name=agent_name,
        greeting_message=greeting_message,
        role_of_bot=role_of_bot,
        company_name=company_name,
    )
    session.add(campaign)
    await session.flush()

    for contact in contacts:
        session.add(
            CampaignContact(
                campaign_id=campaign.id,
                first_name=contact["first_name"],
                phone_e164=contact["phone_e164"],
            )
        )

    await session.commit()
    await session.refresh(campaign)
    return campaign
