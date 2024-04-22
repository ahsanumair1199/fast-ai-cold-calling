from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime
# END IMPORTS


class CampaignBase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_name: str = Field(default=None, max_length=50)
    agent_name: str = Field(default=None, max_length=50)
    role_of_bot: str = Field(default=None, max_length=50)
    greeting_message: str = Field(default=None, max_length=255)
    company_name: str = Field(default=None, max_length=50)
    user_id: Optional[int] = Field(default=None, foreign_key='user.id')
    created_at: datetime = Field(default_factory=datetime.utcnow)
