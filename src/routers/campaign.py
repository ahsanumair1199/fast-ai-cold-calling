from fastapi import Request, APIRouter, Depends, Form, UploadFile, File
from starlette.responses import Response, FileResponse
import json
import os
from sqlmodel import Session, select
from ..utils.db import engine, get_redis
import aioredis
from ..models.voice_model import Voice
from ..models.campaign_model import CampaignBase
from ..utils.helpers import get_current_user
from ..utils.file_validations import validate_excel
from ..signals.campaign_signals import on_campaign_created
from sqlalchemy import event
# END IMPORTS


# ROUTER INITIATION
campaign_router = APIRouter()


@campaign_router.get("/download-sample")
async def download_sample(current_user_id: str = Depends(get_current_user)):
    file_name = "sample.xlsx"
    file_path = os.path.abspath("static/sample.xlsx")
    return FileResponse(file_path, media_type='application/octet-stream', filename=file_name)


# EXCEL FILE HANDLING API
# TRIGGER SIGNAL WHEN CAMPAIGN CREATES
event.listen(CampaignBase, 'after_insert', on_campaign_created)


@campaign_router.post('/campaign-call', tags=['campaign call'])
async def campaign_call(
    request: Request,
    current_user_id: str = Depends(get_current_user),
    campaign_name: str = Form(...),
    agent_name: str = Form(...),
    greeting_message: str = Form(...),
    industry: str = Form(...),
    role_of_bot: str = Form(...),
    file: UploadFile = File(...),
    redis: aioredis.Redis = Depends(get_redis)
):

    excel_data_list = await validate_excel(file)
    for record in excel_data_list:
        target_first_name = record['first_name']
        phone_number = record['phone']
        contact_json = json.dumps({'user_id': current_user_id,
                                   'target_first_name': target_first_name,
                                   'phone_number': phone_number,
                                   'agent_name': agent_name,
                                   'greeting_message': greeting_message,
                                   'industry': industry,
                                   'role_of_bot': role_of_bot,
                                   'access_token': request.headers.get('authorization').split(' ')[1]
                                   })
        await redis.rpush(f"user_id:{current_user_id}:contact_queue", contact_json)

    with Session(engine) as db:
        new_campaign = CampaignBase(
            campaign_name=campaign_name,
            agent_name=agent_name,
            role_of_bot=role_of_bot,
            greeting_message=greeting_message,
            company_name=industry,
            user_id=current_user_id,
        )
        db.add(new_campaign)
        db.commit()
        db.refresh(new_campaign)
    return Response(content=json.dumps({'message': 'Campaign Created'}), media_type='application/json', status_code=200)
