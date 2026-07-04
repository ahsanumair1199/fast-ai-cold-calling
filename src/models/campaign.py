import enum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ContactStatus(str, enum.Enum):
    PENDING = "pending"
    DIALING = "dialing"
    COMPLETED = "completed"
    FAILED = "failed"


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    campaign_name: Mapped[str] = mapped_column(String(255))

    # Persona — data-driven, not hardcoded Python constants.
    agent_name: Mapped[str] = mapped_column(String(100))
    greeting_message: Mapped[str] = mapped_column(String(1000))
    role_of_bot: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255))

    contacts: Mapped[list["CampaignContact"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignContact(Base, TimestampMixin):
    __tablename__ = "campaign_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    phone_e164: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=ContactStatus.PENDING.value, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    call_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)

    campaign: Mapped[Campaign] = relationship(back_populates="contacts")
