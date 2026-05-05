from unittest.mock import patch

from app.services.ai_provider import OpenAIProvider, build_provider


def test_openai_provider_sets_default_timeout():
    with patch("openai.OpenAI") as openai:
        OpenAIProvider("key")

    openai.assert_called_once_with(api_key="key", timeout=120)


def test_build_provider_allows_openai_timeout_override():
    with patch("openai.OpenAI") as openai:
        build_provider("openai", {"api_key": "key", "timeout": 45})

    openai.assert_called_once_with(api_key="key", timeout=45)
