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

    # Database — SQLite is the supported and recommended database.
    # The path inside the container should always be under /data so it lands
    # on the mounted persistent volume.
    DATABASE_URL: str = "sqlite:///./data/immich_gpt.db"

    # Redis / RQ — optional.  Leave blank (default) to run jobs in-process
    # via the built-in ThreadPoolExecutor.  Set to a Redis URL only if you
    # already run Redis on your home lab and want distributed workers.
    REDIS_URL: str = ""

    # Number of background job threads (in-process executor).
    # Ignored when REDIS_URL is set.
    WORKER_CONCURRENCY: int = 2

    # Immich
    IMMICH_URL: str = ""
    IMMICH_API_KEY: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Image limits
    MAX_IMAGE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    THUMBNAIL_WIDTH: int = 512
    THUMBNAIL_HEIGHT: int = 512

    # Session cookie
    # SESSION_COOKIE_SECURE controls whether the Set-Cookie header includes the
    # Secure flag.  Browsers silently discard Secure cookies over plain HTTP,
    # which breaks login entirely on non-TLS deployments.
    #
    # Default is False so that out-of-the-box HTTP deployments (Unraid, home
    # lab, Docker on a LAN) work without any extra configuration.
    # Set SESSION_COOKIE_SECURE=true when the app is served over HTTPS
    # (e.g. behind an Nginx / Caddy reverse proxy with TLS).
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "strict"

    # Secret key — must be a strong random value (≥ 32 chars).
    # The Docker entrypoint auto-generates and persists one in /data/.secret_key
    # when this is not supplied.  Generate manually with:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = ""

    # CORS — comma-separated list of allowed origins.
    # Leave blank when the frontend is served by the same origin as the API
    # (the normal single-container case).  Set explicitly if you run the
    # frontend dev server separately:
    #   CORS_ORIGINS=http://localhost:3000,https://myapp.example.com
    CORS_ORIGINS: str = ""

    # Logging — controls the root logger level.
    # Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL: str = "INFO"

    # Rate limiting — disable in test environments to avoid shared-IP collisions.
    RATELIMIT_ENABLED: bool = True

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

    @property
    def thumbnail_size(self) -> tuple:
        return (self.THUMBNAIL_WIDTH, self.THUMBNAIL_HEIGHT)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
