from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import User
from ..schemas.voice import VoiceOut, VoiceUpdate
from ..services.auth_service import get_current_user
from ..services.voice_service import get_user_voice_id, set_user_voice_id

voices_router = APIRouter(prefix="/voices", tags=["voices"])


@voices_router.get("/me", response_model=VoiceOut)
async def get_my_voice(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    voice_id = await get_user_voice_id(session, user.id)
    return VoiceOut(voice_id=voice_id)


@voices_router.put("/me", response_model=VoiceOut)
async def update_my_voice(
    data: VoiceUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    voice = await set_user_voice_id(session, user.id, data.voice_id)
    return VoiceOut(voice_id=voice.voice_id)
