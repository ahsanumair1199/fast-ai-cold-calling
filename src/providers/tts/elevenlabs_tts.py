import asyncio
import base64
import json
from collections.abc import AsyncIterator

import websockets

from ...core.interfaces import TtsProvider


class ElevenLabsTtsProvider(TtsProvider):
    """ElevenLabs' streaming-input protocol closes its socket at the end of each
    generation (an empty ``text`` message ends the turn and the server then sends
    a close frame) — verified empirically, no documented way to keep one socket
    alive across turns without their separate multi-context API. So connect()/
    close() are no-ops here and a fresh socket is opened per turn inside
    stream_speech() instead; that still satisfies the TtsProvider contract since
    callers only ever see connect() once at call start and close() once at call end.
    """

    def __init__(self, api_key: str, voice_id: str, model_id: str) -> None:
        self._api_key = api_key
        self._uri = (
            f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
            f"?model_id={model_id}&output_format=ulaw_8000"
        )

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def stream_speech(self, text_chunks: AsyncIterator[str]) -> AsyncIterator[bytes]:
        async with websockets.connect(self._uri) as ws:
            await ws.send(
                json.dumps(
                    {
                        "text": " ",
                        "voice_settings": {"stability": 0.5, "similarity_boost": True},
                        "xi_api_key": self._api_key,
                    }
                )
            )

            async def sender() -> None:
                async for chunk in text_chunks:
                    await ws.send(json.dumps({"text": chunk, "try_trigger_generation": True}))
                await ws.send(json.dumps({"text": ""}))

            send_task = asyncio.create_task(sender())
            try:
                async for message in ws:
                    data = json.loads(message)
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    if data.get("isFinal"):
                        break
            finally:
                send_task.cancel()
