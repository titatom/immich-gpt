from pydantic_settings import BaseSettings
from typing import Optional, List


_DEFAULT_SECRET_KEY = "change-me-in-production"


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

    # Secret used for signing tokens / CSRF (must be changed in production)
    SECRET_KEY: str = _DEFAULT_SECRET_KEY

    # CORS — comma-separated list of allowed origins, e.g. "http://localhost:3000,https://myapp.example.com"
    # Set to "*" only in local dev where credentials are not used.
    # When left empty the default tightens to same-origin only (no explicit CORS headers).
    CORS_ORIGINS: str = ""

    # Admin bootstrap: credentials used when no users exist on startup.
    # Defaults to admin / admin so a fresh install is immediately usable.
    # The user is forced to change the password on first login.
    # Empty strings are treated as "not configured" — built-in defaults apply.
    # Set ADMIN_SKIP_BOOTSTRAP=true to suppress auto-creation entirely.
    ADMIN_EMAIL: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_USERNAME: str = "admin"
    ADMIN_SKIP_BOOTSTRAP: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Return the parsed list of allowed CORS origins."""
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def secret_key_is_default(self) -> bool:
        return self.SECRET_KEY == _DEFAULT_SECRET_KEY

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
