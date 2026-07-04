from pydantic import BaseModel


class CampaignOut(BaseModel):
    id: int
    campaign_name: str
    contact_count: int
    skipped_rows: list[str] = []


class ContactOut(BaseModel):
    id: int
    first_name: str
    phone_e164: str
    status: str
    attempt_count: int
    call_sid: str | None

    model_config = {"from_attributes": True}
