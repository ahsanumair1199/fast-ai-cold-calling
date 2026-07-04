"""One-off script: synthesizes a sample 'caller reply' utterance via ElevenLabs
and saves it as raw mulaw/8000 bytes, for use as fake inbound audio in
simulate_call.py. Requires a real ELEVENLABS_API_KEY. Not part of CI.
"""

import asyncio
from pathlib import Path

from src.config import get_settings
from src.providers.tts.elevenlabs_tts import ElevenLabsTtsProvider

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_reply.ulaw"
REPLY_TEXT = "Yes, actually I am interested, can you tell me a bit more about the pricing?"


async def gen(text: str):
    for word in text.split(" "):
        yield word + " "


async def main() -> None:
    settings = get_settings()
    tts = ElevenLabsTtsProvider(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_default_voice_id,
        model_id=settings.elevenlabs_model_id,
    )
    await tts.connect()
    audio = bytearray()
    async for chunk in tts.stream_speech(tts.sentence_chunk(gen(REPLY_TEXT))):
        audio.extend(chunk)
    await tts.close()

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_bytes(bytes(audio))
    print(f"Wrote {len(audio)} bytes to {FIXTURE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
