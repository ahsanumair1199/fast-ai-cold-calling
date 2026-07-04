import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

from .call_session import CallSession

SendAudio = Callable[[bytes], Awaitable[None]]


class CallPipeline:
    """STT -> LLM -> TTS orchestration with barge-in, decoupled from any
    particular telephony wire format: callers hand in a raw inbound-audio
    byte stream and an outbound-audio sink, already in the provider's codec."""

    def __init__(self, session: CallSession, send_audio_out: SendAudio) -> None:
        self._session = session
        self._send_audio_out = send_audio_out
        self._turn_task: asyncio.Task | None = None
        self._pending_turn = False

    async def run(self, inbound_audio: AsyncIterator[bytes]) -> None:
        session = self._session
        await session.stt.connect()
        await session.tts.connect()
        try:
            # Outbound cold call: the agent speaks first, before any user audio arrives.
            self._start_turn()

            pump = asyncio.create_task(self._pump_inbound(inbound_audio))
            consume = asyncio.create_task(self._consume_transcripts())
            done, pending = await asyncio.wait({pump, consume}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            if self._turn_task and not self._turn_task.done():
                self._turn_task.cancel()
            for task in done:
                task.result()
        finally:
            await session.stt.close()
            await session.tts.close()

    async def _pump_inbound(self, inbound_audio: AsyncIterator[bytes]) -> None:
        async for chunk in inbound_audio:
            await self._session.stt.send_audio(chunk)

    async def _consume_transcripts(self) -> None:
        session = self._session
        async for transcript in session.stt.transcripts():
            turn_active = self._turn_task is not None and not self._turn_task.done()
            if transcript.speech_started and turn_active:
                session.barge_in.interrupt.set()
            if transcript.is_final and transcript.text.strip():
                session.history.append({"role": "user", "content": transcript.text})
                if turn_active and not session.barge_in.interrupt.is_set():
                    # Bot is mid-reply and this wasn't a genuine barge-in (e.g. Deepgram
                    # split one utterance into two "final" segments) — let it finish,
                    # then pick up this new content instead of cutting the reply short.
                    self._pending_turn = True
                else:
                    self._start_turn()

    def _start_turn(self) -> None:
        self._pending_turn = False
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        self._turn_task = asyncio.create_task(self._run_turn_then_check_pending())

    async def _run_turn_then_check_pending(self) -> None:
        await self._handle_turn()
        if self._pending_turn:
            self._start_turn()

    async def _handle_turn(self) -> None:
        session = self._session
        session.barge_in.interrupt.clear()
        session.barge_in.bot_speaking.set()
        messages = [{"role": "system", "content": session.system_prompt()}, *session.history]
        full_reply: list[str] = []

        async def tokens() -> AsyncIterator[str]:
            async for delta in session.llm.stream_reply(messages):
                full_reply.append(delta)
                yield delta

        try:
            sentence_stream = session.tts.sentence_chunk(tokens())
            async for audio_chunk in session.tts.stream_speech(sentence_stream):
                if session.barge_in.interrupt.is_set():
                    break
                await self._send_audio_out(audio_chunk)
        finally:
            session.barge_in.bot_speaking.clear()
            if full_reply:
                session.history.append({"role": "assistant", "content": "".join(full_reply)})
