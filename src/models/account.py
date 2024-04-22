from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime


class UserBase(SQLModel):
    first_name: str
    last_name: str
    email: str
    password: str


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    email: str
    username: str = Field(default="")
    password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserLogin(SQLModel):
    email: str
    password: str