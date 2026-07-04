import json
from dataclasses import asdict

from ..redis_client import get_redis_pool
from .call_session import PersonaConfig

PENDING_TTL_SECONDS = 300
ACTIVE_TTL_SECONDS = 1800


def _pending_key(call_sid: str) -> str:
    return f"call_pending:{call_sid}"


def _active_key(call_sid: str) -> str:
    return f"call_active:{call_sid}"


async def set_pending_session(call_sid: str, *, user_id: int, persona: PersonaConfig, voice_id: str) -> None:
    redis = get_redis_pool()
    payload = json.dumps({"user_id": user_id, "voice_id": voice_id, "persona": asdict(persona)})
    await redis.set(_pending_key(call_sid), payload, ex=PENDING_TTL_SECONDS)


async def promote_to_active(call_sid: str) -> dict | None:
    """Called from the /calls/twiml webhook. Moves the pending record (written by
    the outbound-call request) into an active, longer-lived record the WS handler
    will read once Twilio's Media Stream connects."""
    redis = get_redis_pool()
    raw = await redis.get(_pending_key(call_sid))
    if raw is None:
        return None
    await redis.delete(_pending_key(call_sid))
    await redis.set(_active_key(call_sid), raw, ex=ACTIVE_TTL_SECONDS)
    return json.loads(raw)


async def consume_active_session(call_sid: str) -> dict | None:
    """Called once from the WS handler. Single-use: deletes on read."""
    redis = get_redis_pool()
    raw = await redis.get(_active_key(call_sid))
    if raw is None:
        return None
    await redis.delete(_active_key(call_sid))
    return json.loads(raw)
