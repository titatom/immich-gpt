"""
Tests 5, 6: structured JSON validation + malformed AI output handling.
Regression: malformed provider responses.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.ai_provider import OpenAIProvider, AIClassificationResult


VALID_RESPONSE = {
    "bucket_name": "Personal",
    "confidence": 0.92,
    "explanation": "This is a family photo taken at home.",
    "description_suggestion": "Family gathering in the living room.",
    "tags": ["family", "indoor", "casual"],
    "subalbum_suggestion": None,
    "review_recommended": False,
}


def make_mock_provider(response_dict: dict) -> OpenAIProvider:
    import json
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.model = "gpt-4o"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(response_dict)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client
    return provider


def test_valid_response_parses_correctly():
    provider = make_mock_provider(VALID_RESPONSE)
    messages = [{"role": "user", "content": "test"}]
    result = provider.classify_asset(messages)

    assert result.bucket_name == "Personal"
    assert result.confidence == 0.92
    assert "family" in result.tags
    assert result.review_recommended is False


def test_missing_required_field_raises():
    bad = {k: v for k, v in VALID_RESPONSE.items() if k != "bucket_name"}
    provider = make_mock_provider(bad)
    with pytest.raises(ValueError, match="Missing required field 'bucket_name'"):
        provider.classify_asset([{"role": "user", "content": "test"}])


def test_invalid_confidence_raises():
    bad = {**VALID_RESPONSE, "confidence": 1.5}
    provider = make_mock_provider(bad)
    with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
        provider.classify_asset([{"role": "user", "content": "test"}])


def test_tags_not_list_raises():
    bad = {**VALID_RESPONSE, "tags": "family, indoor"}
    provider = make_mock_provider(bad)
    with pytest.raises(ValueError, match="tags must be a list"):
        provider.classify_asset([{"role": "user", "content": "test"}])


def test_malformed_json_raises():
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.model = "gpt-4o"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not json at all {{"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    with pytest.raises(ValueError, match="Invalid JSON"):
        provider.classify_asset([{"role": "user", "content": "test"}])


def test_image_injected_into_user_message():
    """Test that image is injected into user message, not passed as URL."""
    provider = make_mock_provider(VALID_RESPONSE)
    messages = [
        {"role": "system", "content": "You are a classifier."},
        {"role": "user", "content": "Classify this asset."},
    ]
    image_payload = {
        "data_url": "data:image/jpeg;base64,/9j/abc123",
        "mime_type": "image/jpeg",
        "size_bytes": 1024,
    }

    provider.classify_asset(messages, image_payload)

    call_args = provider._client.chat.completions.create.call_args
    sent_messages = call_args.kwargs["messages"]
    user_msg = next(m for m in sent_messages if m["role"] == "user")
    content = user_msg["content"]

    # Content should be a list with image_url entry
    assert isinstance(content, list)
    image_parts = [p for p in content if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    # No raw http URL
    assert "http://" not in image_parts[0]["image_url"]["url"]


def test_subalbum_can_be_null():
    response = {**VALID_RESPONSE, "subalbum_suggestion": None}
    provider = make_mock_provider(response)
    result = provider.classify_asset([{"role": "user", "content": "test"}])
    assert result.subalbum_suggestion is None


def test_tags_capped_at_20():
    response = {**VALID_RESPONSE, "tags": [f"tag{i}" for i in range(30)]}
    provider = make_mock_provider(response)
    result = provider.classify_asset([{"role": "user", "content": "test"}])
    assert len(result.tags) <= 20
