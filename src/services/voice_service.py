from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import Voice


async def get_user_voice_id(session: AsyncSession, user_id: int) -> str:
    voice = await session.scalar(select(Voice).where(Voice.user_id == user_id))
    if voice is not None:
        return voice.voice_id
    return get_settings().elevenlabs_default_voice_id


async def set_user_voice_id(session: AsyncSession, user_id: int, voice_id: str) -> Voice:
    voice = await session.scalar(select(Voice).where(Voice.user_id == user_id))
    if voice is None:
        voice = Voice(user_id=user_id, voice_id=voice_id)
        session.add(voice)
    else:
        voice.voice_id = voice_id
    await session.commit()
    await session.refresh(voice)
    return voice
