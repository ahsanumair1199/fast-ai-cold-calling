import asyncio

from twilio.rest import Client

from ..config import get_settings
from ..core.call_session import PersonaConfig
from ..core.session_store import set_pending_session


async def place_outbound_call(*, user_id: int, phone_e164: str, persona: PersonaConfig, voice_id: str) -> str:
    """Creates the Twilio call and stores the pending webhook-handoff record.
    Shared by the ad-hoc /calls/outbound endpoint and the campaign dialer —
    always uses server-owned Twilio credentials, never a caller's JWT."""
    settings = get_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    base = settings.server_address.rstrip("/")

    call = await asyncio.to_thread(
        client.calls.create,
        to=phone_e164,
        from_=settings.twilio_phone_number,
        url=f"{base}/calls/twiml",
        status_callback=f"{base}/calls/status",
        status_callback_event=["completed", "no-answer", "busy", "failed"],
    )
    await set_pending_session(call.sid, user_id=user_id, persona=persona, voice_id=voice_id)
    return call.sid
