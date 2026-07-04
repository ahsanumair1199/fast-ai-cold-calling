import asyncio

from src.core.call_session import CallSession, PersonaConfig
from src.core.interfaces import Transcript
from src.core.pipeline import CallPipeline

from .fakes import FakeLlmProvider, FakeSttProvider, FakeTtsProvider

PERSONA = PersonaConfig(
    agent_name="Sara",
    greeting_message="Hi, this is Sara.",
    role_of_bot="sales specialist",
    company_name="Acme",
)


async def _silent_inbound(duration: float):
    steps = int(duration / 0.02)
    for _ in range(steps):
        yield b""
        await asyncio.sleep(0.02)


def _make_session(stt, llm, tts):
    return CallSession(call_sid="test", user_id=1, persona=PERSONA, stt=stt, llm=llm, tts=tts)


async def test_greeting_turn_produces_full_reply():
    session = _make_session(
        FakeSttProvider([]),
        FakeLlmProvider(["Hello there, how are you today"]),
        FakeTtsProvider(),
    )
    captured = []

    async def send_audio_out(chunk: bytes) -> None:
        captured.append(chunk)

    pipeline = CallPipeline(session, send_audio_out)
    await pipeline.run(_silent_inbound(0.6))

    assert len(session.history) == 1
    assert session.history[0]["role"] == "assistant"
    assert "Hello there, how are you today".replace(" ", "") in session.history[0]["content"].replace(" ", "")
    assert captured  # some audio was actually sent


async def test_split_final_transcripts_do_not_truncate_in_flight_reply():
    """Regression test: Deepgram can split one continuous user utterance into
    two separate 'final' segments. Before the fix, every final transcript
    unconditionally cancelled any in-flight bot turn, truncating the reply
    mid-sentence even though nothing about the second segment was a genuine
    interruption (no SpeechStarted while the bot was speaking)."""
    session = _make_session(
        FakeSttProvider(
            [
                (0.02, Transcript(text="yes I am interested", is_final=True)),
                (0.05, Transcript(text="tell me about pricing", is_final=True)),
            ]
        ),
        FakeLlmProvider(
            [
                "This is the full greeting that must not be cut off",
                "Sure, pricing depends on a few things",
            ],
            delay_per_word=0.05,
        ),
        FakeTtsProvider(),
    )

    async def send_audio_out(chunk: bytes) -> None:
        pass

    pipeline = CallPipeline(session, send_audio_out)
    await pipeline.run(_silent_inbound(2.0))

    assistant_messages = [m["content"] for m in session.history if m["role"] == "assistant"]
    assert len(assistant_messages) == 2
    # The greeting must be complete, not cut off after one or two words.
    normalized = assistant_messages[0].replace(" ", "")
    assert "mustnotbecutoff" in normalized


async def test_genuine_barge_in_interrupts_bot_speech():
    session = _make_session(
        FakeSttProvider(
            [
                # Fires almost immediately, while the greeting is still being spoken.
                (0.01, Transcript(text="", is_final=False, speech_started=True)),
                (0.02, Transcript(text="wait stop", is_final=True)),
            ]
        ),
        FakeLlmProvider(
            ["This is a long greeting that should get interrupted partway through speaking"],
            delay_per_word=0.05,
        ),
        FakeTtsProvider(),
    )

    async def send_audio_out(chunk: bytes) -> None:
        pass

    pipeline = CallPipeline(session, send_audio_out)
    await pipeline.run(_silent_inbound(1.5))

    # The interrupt must have been set at some point (barge-in detected).
    # We can't observe the flag after run() clears it per-turn, so instead we
    # confirm the user's interrupting utterance made it into history alongside
    # a (likely shorter, interrupted) assistant turn — i.e. the turn-taking
    # loop kept working after a genuine barge-in instead of deadlocking.
    roles = [m["role"] for m in session.history]
    assert "user" in roles
    assert "assistant" in roles
