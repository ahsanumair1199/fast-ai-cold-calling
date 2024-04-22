from fastapi import Request, APIRouter, Depends
from starlette.responses import Response
import json
import os
from sqlmodel import Session, select
from ..utils.db import engine
from ..models.voice_model import Voice
from ..utils.helpers import get_current_user
from ..constants.common import ELEVENLABS_API_KEY
import requests
# END IMPORTS

# ROUTER INITIATION
voices_router = APIRouter()


# SET VOICE
@voices_router.post('/set-voice')
async def set_voice(request: Request, current_user_id: str = Depends(get_current_user)):
    data = await request.json()
    with Session(engine) as db:
        statement = select(Voice).where(Voice.user_id == current_user_id)
        results = db.exec(statement)
        voice_instance = results.one()
        voice_instance.voice_id = data['voice_id']
        db.add(voice_instance)
        db.commit()
        db.refresh(voice_instance)
    return Response(json.dumps(data['voice_id']))

# GET VOICE


@voices_router.get('/get-voice')
async def get_voice(request: Request, current_user_id: str = Depends(get_current_user)):
    with Session(engine) as db:
        statement = select(Voice).where(Voice.user_id == current_user_id)
        results = db.exec(statement)
        voice_instance = results.one()
    url = f"https://api.elevenlabs.io/v1/voices/{voice_instance.voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    response = requests.request("GET", url, headers=headers)
    print(response.content)
    return Response(response.content)
