from typing import Optional
from sqlmodel import Field, SQLModel

class Voice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    voice_id: str
    user_id: Optional[int] = Field(default=None, foreign_key='user.id')