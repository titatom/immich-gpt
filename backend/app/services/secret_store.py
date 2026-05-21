"""Small symmetric encryption helper for runtime-stored API keys.

The app already requires a high-entropy SECRET_KEY.  Deriving an encryption key
from it lets us avoid storing newly saved provider/Immich API keys as plaintext
without introducing another operator-managed secret.
"""
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return value
    if value.startswith(_PREFIX):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{_PREFIX}{token}"


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return value
    if not value.startswith(_PREFIX):
        # Backwards compatibility for existing plaintext rows.
        return value
    token = value[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored secret could not be decrypted with the configured SECRET_KEY") from exc


def is_encrypted_secret(value: Optional[str]) -> bool:
    return bool(value and value.startswith(_PREFIX))


def has_secret(value: Optional[str]) -> bool:
    return bool(decrypt_secret(value))
