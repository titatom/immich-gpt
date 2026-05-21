import pytest

from app.config import settings
from app.services.url_validation import ServiceUrlError, validate_service_url


def test_validate_service_url_blocks_loopback_by_default(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_SERVICE_URLS", False)

    with pytest.raises(ServiceUrlError):
        validate_service_url("http://127.0.0.1:11434", field_name="Ollama URL")


def test_validate_service_url_allows_private_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_SERVICE_URLS", True)

    assert validate_service_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"


def test_validate_service_url_blocks_link_local_even_when_private_allowed(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_SERVICE_URLS", True)

    with pytest.raises(ServiceUrlError):
        validate_service_url("http://169.254.169.254/latest/meta-data")


def test_validate_service_url_rejects_credentials(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_SERVICE_URLS", True)

    with pytest.raises(ServiceUrlError):
        validate_service_url("https://user:pass@example.com")
