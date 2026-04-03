"""Test 2: metadata inclusion in provider request + ImmichClient behavior."""
import pytest
from unittest.mock import MagicMock, patch
import httpx
from app.services.immich_client import ImmichClient, ImmichError


def make_mock_response(status_code: int, json_data=None, content=b""):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    resp.content = content
    resp.text = str(json_data)
    return resp


def test_check_connectivity_success():
    client = ImmichClient("http://immich.local", "test-key")
    mock_http = MagicMock()
    mock_http.__enter__ = lambda self: self
    mock_http.__exit__ = MagicMock(return_value=False)
    mock_http.get.side_effect = [
        make_mock_response(200, {"res": "pong"}),
        make_mock_response(200, {"version": "1.0"}),
    ]

    with patch.object(client, "_client", return_value=mock_http):
        result = client.check_connectivity()
    assert result["connected"] is True


def test_check_connectivity_failure_raises():
    client = ImmichClient("http://bad-host", "key")
    mock_http = MagicMock()
    mock_http.__enter__ = lambda self: self
    mock_http.__exit__ = MagicMock(return_value=False)
    mock_http.get.return_value = make_mock_response(401, {"message": "Unauthorized"})

    with patch.object(client, "_client", return_value=mock_http):
        with pytest.raises(ImmichError):
            client.check_connectivity()


def test_get_thumbnail_returns_bytes():
    client = ImmichClient("http://immich.local", "key")
    fake_bytes = b"\xff\xd8\xff\xe0test"
    mock_http = MagicMock()
    mock_http.__enter__ = lambda self: self
    mock_http.__exit__ = MagicMock(return_value=False)
    mock_http.get.return_value = make_mock_response(200, content=fake_bytes)

    with patch.object(client, "_client", return_value=mock_http):
        result = client.get_thumbnail("asset-123")
    assert result == fake_bytes


def test_get_thumbnail_raises_on_404():
    client = ImmichClient("http://immich.local", "key")
    mock_http = MagicMock()
    mock_http.__enter__ = lambda self: self
    mock_http.__exit__ = MagicMock(return_value=False)
    mock_http.get.return_value = make_mock_response(404, {"error": "Not found"})

    with patch.object(client, "_client", return_value=mock_http):
        with pytest.raises(ImmichError, match="Thumbnail unavailable"):
            client.get_thumbnail("missing-asset")


def test_api_key_sent_in_header():
    """Verify credentials are sent in headers, not in URL."""
    client = ImmichClient("http://immich.local", "my-secret-key")
    http_client = client._client()
    assert http_client.headers.get("x-api-key") == "my-secret-key"
    # Key should not be in the base URL
    assert "my-secret-key" not in str(http_client.base_url)


def test_is_external_library_asset_detection():
    client = ImmichClient("http://immich.local", "key")
    external_asset = {"library": {"type": "EXTERNAL"}}
    internal_asset = {"library": {"type": "UPLOAD"}}
    no_lib_asset = {}

    assert client.is_external_library_asset(external_asset) is True
    assert client.is_external_library_asset(internal_asset) is False
    assert client.is_external_library_asset(no_lib_asset) is False
