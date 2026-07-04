from dataclasses import dataclass, field

from .barge_in import BargeInEvents
from .interfaces import LlmProvider, Message, SttProvider, TtsProvider


@dataclass(frozen=True)
class PersonaConfig:
    agent_name: str
    greeting_message: str
    role_of_bot: str
    company_name: str
    target_first_name: str = "there"


@dataclass
class CallSession:
    """Everything the old app kept as module-level globals, scoped to one call."""

    call_sid: str
    user_id: int
    persona: PersonaConfig
    stt: SttProvider
    llm: LlmProvider
    tts: TtsProvider
    stream_sid: str | None = None
    history: list[Message] = field(default_factory=list)
    barge_in: BargeInEvents = field(default_factory=BargeInEvents)

    def system_prompt(self) -> str:
        p = self.persona
        return (
            f"You are {p.agent_name}, a {p.role_of_bot} at {p.company_name}. "
            f"You are the one who called {p.target_first_name} — they did not call you. "
            f"Open the conversation with this greeting, in your own natural words: {p.greeting_message}. "
            "Keep replies short and conversational, like a real phone call, not an assistant. "
            "Never say things like 'how can I assist you today'."
        )
