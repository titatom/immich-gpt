from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Immich GPT"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False

    # Database — PostgreSQL recommended for production; SQLite for dev/test
    DATABASE_URL: str = "sqlite:///./data/immich_gpt.db"

    # Redis / RQ
    # Set to empty string "" to disable Redis entirely and use the built-in
    # in-process thread-pool executor (suitable for single-container dev only).
    REDIS_URL: str = ""

    # Worker concurrency for the in-process executor (ignored when Redis is used)
    WORKER_CONCURRENCY: int = 2

    # Immich (legacy env-var fallback for single-user dev setups only)
    IMMICH_URL: str = ""
    IMMICH_API_KEY: str = ""

    # OpenAI (legacy env-var fallback)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Image limits
    MAX_IMAGE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    THUMBNAIL_SIZE: tuple = (512, 512)

    # Session cookie
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_SECURE: bool = False  # Set True in production (HTTPS)
    SESSION_COOKIE_SAMESITE: str = "lax"

    # Admin bootstrap: if no users exist on startup, create this admin account
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_USERNAME: str = "admin"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
