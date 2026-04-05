import os
import secrets
import logging
from pydantic_settings import BaseSettings
from pydantic import model_validator

logger = logging.getLogger(__name__)

_PLACEHOLDER_KEY = "change-me-in-production"


def _persist_secret_key(key: str) -> None:
    """Write the auto-generated SECRET_KEY into .env so it survives restarts."""
    env_path = ".env"
    try:
        lines: list[str] = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        # Replace existing SECRET_KEY line or append a new one
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith("SECRET_KEY="):
                lines[i] = f"SECRET_KEY={key}\n"
                replaced = True
                break
        if not replaced:
            lines.append(f"\n# Auto-generated at first startup — do not share\nSECRET_KEY={key}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except OSError:
        # Read-only filesystem (e.g. some container setups) — key lives only in memory
        pass


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Immich GPT"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./data/immich_gpt.db"

    # Redis / RQ
    # Set to empty string "" to disable Redis entirely and use the built-in
    # in-process thread-pool executor (suitable for single-container deployments).
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

    # Auth — set AUTH_ENABLED=true and SECRET_KEY to require Bearer token.
    # If SECRET_KEY is left as the placeholder a secure random key is generated
    # automatically at startup and persisted to .env.
    SECRET_KEY: str = _PLACEHOLDER_KEY
    AUTH_ENABLED: bool = False

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> "Settings":
        if self.SECRET_KEY == _PLACEHOLDER_KEY:
            generated = secrets.token_urlsafe(32)
            self.SECRET_KEY = generated
            _persist_secret_key(generated)
            logger.warning(
                "SECRET_KEY was the insecure placeholder. "
                "A new random key has been generated and written to .env. "
                "Set AUTH_ENABLED=true to enforce Bearer-token authentication."
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def warn_if_auth_disabled() -> None:
    """Emit a startup warning when authentication is disabled."""
    if not settings.AUTH_ENABLED:
        logger.warning(
            "AUTH_ENABLED=false — the API is open to anyone who can reach this "
            "host. Set AUTH_ENABLED=true and use the generated SECRET_KEY as a "
            "Bearer token to restrict access."
        )
