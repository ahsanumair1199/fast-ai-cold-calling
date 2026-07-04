import asyncio
from collections.abc import AsyncIterator

from src.core.interfaces import LlmProvider, Message, SttProvider, Transcript, TtsProvider


class FakeSttProvider(SttProvider):
    """Replays a scripted list of (delay_seconds, Transcript) pairs."""

    def __init__(self, scripted_events: list[tuple[float, Transcript]]) -> None:
        self._scripted = scripted_events
        self._queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        # Mirrors the real adapters: the transcript stream stays open for the
        # life of the call and only ends when close() cancels this task (whose
        # `finally` then pushes the sentinel) — it does NOT end just because
        # we've run out of scripted events, same as a live STT socket wouldn't.
        try:
            for delay, event in self._scripted:
                await asyncio.sleep(delay)
                await self._queue.put(event)
            await asyncio.Event().wait()
        finally:
            await self._queue.put(None)

    async def send_audio(self, chunk: bytes) -> None:
        pass

    async def transcripts(self) -> AsyncIterator[Transcript]:
        while True:
            item = await self._queue.get()
            if item is None:
                return
            yield item

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()


class FakeLlmProvider(LlmProvider):
    """Returns a scripted reply per call, in order; repeats the last one if
    called more times than scripted. Each word is yielded with a delay, so
    tests can control how long a "turn" stays in flight."""

    def __init__(self, replies: list[str], delay_per_word: float = 0.03) -> None:
        self._replies = replies
        self._delay = delay_per_word
        self._call_count = 0

    async def stream_reply(self, messages: list[Message]) -> AsyncIterator[str]:
        index = min(self._call_count, len(self._replies) - 1)
        self._call_count += 1
        for word in self._replies[index].split(" "):
            await asyncio.sleep(self._delay)
            yield word + " "


class FakeTtsProvider(TtsProvider):
    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def stream_speech(self, text_chunks: AsyncIterator[str]) -> AsyncIterator[bytes]:
        async for chunk in text_chunks:
            await asyncio.sleep(0.01)
            yield chunk.encode()
