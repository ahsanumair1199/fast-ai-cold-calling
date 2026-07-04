from ..config import Settings
from ..core.interfaces import LlmProvider, SttProvider, TtsProvider
from .llm.openai_llm import OpenAiLlmProvider
from .stt.deepgram_stt import DeepgramSttProvider
from .tts.elevenlabs_tts import ElevenLabsTtsProvider


def build_stt(settings: Settings) -> SttProvider:
    return DeepgramSttProvider(api_key=settings.deepgram_api_key, model=settings.deepgram_model)


def build_tts(settings: Settings, voice_id: str) -> TtsProvider:
    return ElevenLabsTtsProvider(
        api_key=settings.elevenlabs_api_key,
        voice_id=voice_id,
        model_id=settings.elevenlabs_model_id,
    )


def build_llm(settings: Settings) -> LlmProvider:
    return OpenAiLlmProvider(api_key=settings.openai_api_key, model=settings.openai_model)
