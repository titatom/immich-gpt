from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List

# Minimum acceptable length for SECRET_KEY (256-bit entropy when hex-encoded).
_SECRET_KEY_MIN_LENGTH = 32

# Well-known placeholder values that must never be used in production.
_WEAK_SECRET_KEYS = {
    "change-me-in-production",
    "secret",
    "changeme",
    "insecure",
    "dev",
    "",
}


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Immich GPT"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False

    # Database — PostgreSQL required for production; SQLite supported for dev/test only.
    DATABASE_URL: str = "sqlite:///./data/immich_gpt.db"

    # Redis / RQ
    REDIS_URL: str = ""

    # Worker concurrency for the in-process executor (ignored when Redis is used)
    WORKER_CONCURRENCY: int = 2

    # Immich
    IMMICH_URL: str = ""
    IMMICH_API_KEY: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Image limits
    MAX_IMAGE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    THUMBNAIL_SIZE: tuple = (512, 512)

    # Session cookie — secure=True and samesite=strict are the secure defaults.
    # Override SESSION_COOKIE_SECURE=false only when running behind a plain HTTP
    # reverse proxy that is not Internet-exposed (e.g. local dev).
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "strict"

    # Secret key used for signing session tokens.
    # Must be set explicitly to a strong random value.
    # Generate with:  python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = ""

    # CORS — comma-separated list of allowed origins, e.g. "http://localhost:3000,https://myapp.example.com"
    CORS_ORIGINS: str = ""

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        key = self.SECRET_KEY
        if key in _WEAK_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY is not set or uses a known weak placeholder. "
                "Set a strong random value in your .env or environment. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(key) < _SECRET_KEY_MIN_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {_SECRET_KEY_MIN_LENGTH} characters long. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        """Return the parsed list of allowed CORS origins."""
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
