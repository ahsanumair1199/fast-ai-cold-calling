"""Replays a pre-recorded 'caller reply' as fake inbound call audio through the
REAL pipeline (Deepgram -> OpenAI -> ElevenLabs, live API calls) and writes the
bot's spoken replies to a file — end-to-end verification without a phone call.

Usage: uv run python -m tests.manual.simulate_call [output_dir]
Requires: real API keys in .env, and tests/manual/fixtures/sample_reply.ulaw
(generate it first with `uv run python -m tests.manual.generate_fixture`).
"""

import asyncio
import sys
from pathlib import Path

from src.config import get_settings
from src.core.call_session import CallSession, PersonaConfig
from src.core.pipeline import CallPipeline
from src.providers.registry import build_llm, build_stt, build_tts

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_reply.ulaw"
FRAME_BYTES = 160  # 20ms of mulaw/8000 mono, matching Twilio's real packet size
FRAME_SECONDS = 0.02
LEAD_SILENCE_SECONDS = 3.0
TRAIL_SILENCE_SECONDS = 12.0
SILENCE_BYTE = b"\xff"


async def fake_inbound_audio():
    """Silence -> a real recorded reply -> trailing silence, paced like a live call."""
    lead_frames = int(LEAD_SILENCE_SECONDS / FRAME_SECONDS)
    for _ in range(lead_frames):
        yield SILENCE_BYTE * FRAME_BYTES
        await asyncio.sleep(FRAME_SECONDS)

    reply_audio = FIXTURE_PATH.read_bytes()
    for i in range(0, len(reply_audio), FRAME_BYTES):
        yield reply_audio[i : i + FRAME_BYTES]
        await asyncio.sleep(FRAME_SECONDS)

    trail_frames = int(TRAIL_SILENCE_SECONDS / FRAME_SECONDS)
    for _ in range(trail_frames):
        yield SILENCE_BYTE * FRAME_BYTES
        await asyncio.sleep(FRAME_SECONDS)


async def main() -> None:
    if not FIXTURE_PATH.exists():
        print(f"Missing fixture: {FIXTURE_PATH}. Run generate_fixture.py first.")
        sys.exit(1)

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out_path = out_dir / "simulate_call_output.ulaw"

    settings = get_settings()
    persona = PersonaConfig(
        agent_name="Sara",
        greeting_message="Hi, this is Sara calling from Acme Roofing about your recent quote request.",
        role_of_bot="sales specialist",
        company_name="Acme Roofing",
        target_first_name="Alex",
    )
    session = CallSession(
        call_sid="SIMULATED",
        user_id=0,
        persona=persona,
        stt=build_stt(settings),
        llm=build_llm(settings),
        tts=build_tts(settings, settings.elevenlabs_default_voice_id),
    )

    captured = bytearray()

    async def send_audio_out(chunk: bytes) -> None:
        captured.extend(chunk)

    pipeline = CallPipeline(session, send_audio_out)
    await pipeline.run(fake_inbound_audio())

    out_path.write_bytes(bytes(captured))
    print(f"Captured {len(captured)} bytes of bot audio -> {out_path}")
    print("--- conversation history ---")
    for msg in session.history:
        print(f"{msg['role']}: {msg['content']}")


if __name__ == "__main__":
    asyncio.run(main())
