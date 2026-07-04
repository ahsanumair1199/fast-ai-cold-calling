from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

Message = dict[str, str]  # {"role": "system"|"user"|"assistant", "content": str}


@dataclass(frozen=True)
class Transcript:
    text: str
    is_final: bool
    speech_started: bool = False  # barge-in trigger: fires the instant new user speech begins


class SttProvider(ABC):
    """One instance per call. connect()/close() bound to call start/end."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def send_audio(self, chunk: bytes) -> None:
        """Forward raw inbound audio bytes (mulaw/8000, unmodified) to the provider."""

    @abstractmethod
    def transcripts(self) -> AsyncIterator[Transcript]: ...

    @abstractmethod
    async def close(self) -> None: ...


class LlmProvider(ABC):
    """Stateless per call — wraps a shared, connection-pooled client."""

    @abstractmethod
    def stream_reply(self, messages: list[Message]) -> AsyncIterator[str]:
        """Yields text deltas as the model generates them."""


class TtsProvider(ABC):
    """One instance per call. connect()/close() bound to call start/end."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def stream_speech(self, text_chunks: AsyncIterator[str]) -> AsyncIterator[bytes]:
        """Consumes sentence-chunked text, yields raw audio bytes already in
        this provider's configured telephony codec/rate (mulaw/8000)."""

    @staticmethod
    async def sentence_chunk(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
        """Splits an LLM token stream into TTS-safe chunks without breaking mid-sentence."""
        splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
        buffer = ""
        async for text in tokens:
            if buffer.endswith(splitters):
                yield buffer + " "
                buffer = text
            elif text.startswith(splitters):
                yield buffer + text[0] + " "
                buffer = text[1:]
            else:
                buffer += text
        if buffer:
            yield buffer + " "
