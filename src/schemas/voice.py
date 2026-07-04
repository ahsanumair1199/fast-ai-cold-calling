from pydantic import BaseModel


class VoiceOut(BaseModel):
    voice_id: str


class VoiceUpdate(BaseModel):
    voice_id: str
