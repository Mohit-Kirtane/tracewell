from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Tracewell"
    cors_origins: list[str] = ["*"]

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "tracewell"

    llm_api_key: str = ""
    llm_api_key_fallback: str = ""
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-3.6-flash"

    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    cookie_secure: bool = False

    worker_poll_interval_seconds: int = 5
    run_worker_inline: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
