import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack

from deepgram import AsyncDeepgramClient
from deepgram.listen import ListenV1Results, ListenV1SpeechStarted

from ...core.interfaces import SttProvider, Transcript


class DeepgramSttProvider(SttProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._model = model
        self._stack = AsyncExitStack()
        self._socket = None
        self._queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        self._pump_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._socket = await self._stack.enter_async_context(
            self._client.listen.v1.connect(
                model=self._model,
                encoding="mulaw",
                sample_rate=8000,
                channels=1,
                interim_results=True,
                vad_events=True,
                smart_format=True,
                endpointing=300,
            )
        )
        self._pump_task = asyncio.create_task(self._pump())

    async def _pump(self) -> None:
        try:
            async for message in self._socket:
                if isinstance(message, ListenV1Results):
                    alternatives = message.channel.alternatives
                    text = alternatives[0].transcript if alternatives else ""
                    if text:
                        await self._queue.put(Transcript(text=text, is_final=bool(message.is_final)))
                elif isinstance(message, ListenV1SpeechStarted):
                    await self._queue.put(Transcript(text="", is_final=False, speech_started=True))
        finally:
            await self._queue.put(None)

    async def send_audio(self, chunk: bytes) -> None:
        await self._socket.send_media(chunk)

    async def transcripts(self) -> AsyncIterator[Transcript]:
        while True:
            item = await self._queue.get()
            if item is None:
                return
            yield item

    async def close(self) -> None:
        if self._pump_task is not None:
            self._pump_task.cancel()
        await self._stack.aclose()
