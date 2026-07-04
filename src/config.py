from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "dev"

    database_url: str = "sqlite+aiosqlite:///./database.db"
    redis_url: str = "redis://localhost:6379/0"

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    elevenlabs_api_key: str
    elevenlabs_default_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_flash_v2_5"

    deepgram_api_key: str
    deepgram_model: str = "nova-2-phonecall"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30

    server_address: str
    cors_allow_origins: list[str] = []
    max_concurrent_calls: int = 5

    api_title: str = "Fast AI Cold Calling"
    api_description: str = "AI voice cold-calling agent"
    api_version: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
