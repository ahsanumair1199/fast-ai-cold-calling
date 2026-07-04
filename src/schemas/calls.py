from pydantic import BaseModel, Field


class OutboundCallRequest(BaseModel):
    phone_number: str = Field(description="Any reasonable format; normalized to E.164")
    agent_name: str
    greeting_message: str
    role_of_bot: str
    company_name: str
    target_first_name: str = "there"


class OutboundCallResponse(BaseModel):
    call_sid: str
