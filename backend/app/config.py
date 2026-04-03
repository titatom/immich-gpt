from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Immich GPT"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./data/immich_gpt.db"

    # Redis / RQ
    REDIS_URL: str = "redis://redis:6379/0"

    # Immich
    IMMICH_URL: str = ""
    IMMICH_API_KEY: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Image limits
    MAX_IMAGE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    THUMBNAIL_SIZE: tuple = (512, 512)

    # Auth — set AUTH_ENABLED=true and SECRET_KEY to require Bearer token
    SECRET_KEY: str = "change-me-in-production"
    AUTH_ENABLED: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
