"""
Test 3 (image handling) + regression: private Immich URL never passed to external AI.
"""
import pytest
import io
import base64
from unittest.mock import MagicMock, patch
from app.services.image_preparation import ImagePreparationService, ImagePreparationError
from app.services.immich_client import ImmichError


def _make_jpeg_bytes() -> bytes:
    """Create a minimal valid JPEG."""
    try:
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(128, 64, 32))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        # Minimal JPEG header bytes
        return b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'


def test_prepare_returns_data_url():
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = _make_jpeg_bytes()

    svc = ImagePreparationService(immich_client=mock_client)
    result = svc.prepare_for_provider("asset-123")

    assert "data_url" in result
    assert result["data_url"].startswith("data:image/")
    assert ";base64," in result["data_url"]


def test_prepare_does_not_return_raw_immich_url():
    """Regression: no raw private URL should appear in the result."""
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = _make_jpeg_bytes()

    svc = ImagePreparationService(immich_client=mock_client)
    result = svc.prepare_for_provider("asset-123")

    # No http or private URL in data_url
    assert "http://" not in result["data_url"]
    assert "https://" not in result["data_url"]
    assert "immich" not in result["data_url"].lower()


def test_prepare_returns_size_bytes():
    mock_client = MagicMock()
    mock_client.get_thumbnail.return_value = _make_jpeg_bytes()

    svc = ImagePreparationService(immich_client=mock_client)
    result = svc.prepare_for_provider("asset-123")
    assert result["size_bytes"] > 0


def test_prepare_raises_on_immich_error():
    mock_client = MagicMock()
    mock_client.get_thumbnail.side_effect = ImmichError("Not found", 404)

    svc = ImagePreparationService(immich_client=mock_client)
    with pytest.raises(ImagePreparationError, match="Could not fetch thumbnail"):
        svc.prepare_for_provider("missing-asset")


def test_prepare_raises_on_oversized_image():
    mock_client = MagicMock()
    # Return oversized payload
    mock_client.get_thumbnail.return_value = b"x" * (25 * 1024 * 1024)

    svc = ImagePreparationService(immich_client=mock_client)
    svc.max_bytes = 1024
    with pytest.raises(ImagePreparationError, match="Image too large"):
        svc.prepare_for_provider("big-asset")


def test_data_url_is_valid_base64():
    mock_client = MagicMock()
    jpeg = _make_jpeg_bytes()
    mock_client.get_thumbnail.return_value = jpeg

    svc = ImagePreparationService(immich_client=mock_client)
    result = svc.prepare_for_provider("asset-x")

    prefix, b64 = result["data_url"].split(";base64,")
    # Should decode without error
    decoded = base64.b64decode(b64)
    assert len(decoded) > 0
