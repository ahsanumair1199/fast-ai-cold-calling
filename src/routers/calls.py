import base64
import json

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from twilio.twiml.voice_response import Connect, VoiceResponse

from ..config import get_settings
from ..core.call_session import CallSession, PersonaConfig
from ..core.pipeline import CallPipeline
from ..core.session_store import consume_active_session, promote_to_active
from ..db import get_session
from ..models import User
from ..providers.registry import build_llm, build_stt, build_tts
from ..schemas.calls import OutboundCallRequest, OutboundCallResponse
from ..services.auth_service import get_current_user
from ..services.call_service import place_outbound_call
from ..services.campaign_dialer import handle_call_status_update
from ..services.voice_service import get_user_voice_id
from ..utils.phone import to_e164
from ..utils.twilio_signature import verify_twilio_signature

calls_router = APIRouter(prefix="/calls", tags=["calls"])


@calls_router.post("/outbound", response_model=OutboundCallResponse)
async def create_outbound_call(
    data: OutboundCallRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    phone_e164 = to_e164(data.phone_number)
    voice_id = await get_user_voice_id(session, user.id)
    persona = PersonaConfig(
        agent_name=data.agent_name,
        greeting_message=data.greeting_message,
        role_of_bot=data.role_of_bot,
        company_name=data.company_name,
        target_first_name=data.target_first_name,
    )
    call_sid = await place_outbound_call(
        user_id=user.id, phone_e164=phone_e164, persona=persona, voice_id=voice_id
    )
    return OutboundCallResponse(call_sid=call_sid)


@calls_router.post("/twiml")
async def twiml_webhook(request: Request):
    await verify_twilio_signature(request)
    form = await request.form()
    call_sid = form.get("CallSid")

    response = VoiceResponse()
    session_data = await promote_to_active(call_sid) if call_sid else None
    if session_data is None:
        response.say("Sorry, this call could not be connected. Goodbye.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    connect = Connect()
    connect.stream(url=f"wss://{request.url.hostname}/calls/stream/{call_sid}")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@calls_router.post("/status")
async def status_webhook(request: Request):
    await verify_twilio_signature(request)
    form = await request.form()
    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")
    if call_sid and call_status:
        await handle_call_status_update(call_sid, call_status)
    return Response(status_code=204)


@calls_router.websocket("/stream/{call_sid}")
async def stream_call(websocket: WebSocket, call_sid: str):
    await websocket.accept()

    stream_sid = None
    while stream_sid is None:
        message = await websocket.receive_text()
        data = json.loads(message)
        event = data.get("event")
        if event == "start":
            start = data["start"]
            if start.get("callSid") != call_sid:
                await websocket.close(code=1008)
                return
            stream_sid = start["streamSid"]
        elif event == "stop":
            return

    session_data = await consume_active_session(call_sid)
    if session_data is None:
        await websocket.close(code=1008)
        return

    settings = get_settings()
    persona = PersonaConfig(**session_data["persona"])
    call_session = CallSession(
        call_sid=call_sid,
        user_id=session_data["user_id"],
        persona=persona,
        stream_sid=stream_sid,
        stt=build_stt(settings),
        llm=build_llm(settings),
        tts=build_tts(settings, session_data["voice_id"]),
    )

    async def send_audio_out(chunk: bytes) -> None:
        await websocket.send_text(
            json.dumps(
                {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": base64.b64encode(chunk).decode("ascii")},
                }
            )
        )

    async def inbound_audio():
        while True:
            try:
                message = await websocket.receive_text()
            except WebSocketDisconnect:
                return
            data = json.loads(message)
            event = data.get("event")
            if event == "media":
                yield base64.b64decode(data["media"]["payload"])
            elif event == "stop":
                return

    pipeline = CallPipeline(call_session, send_audio_out)
    try:
        await pipeline.run(inbound_audio())
    except WebSocketDisconnect:
        pass
