"""
ImagePreparationService:
- fetches image bytes from Immich
- validates content type and file size
- resizes if needed
- converts to base64 data URL
- returns provider-safe image payload

Never exposes private Immich URLs to external AI providers.
"""
import base64
import io
from typing import Optional, Tuple
from ..config import settings
from .immich_client import ImmichClient, ImmichError

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "image/webp", "image/bmp", "image/tiff",
}


class ImagePreparationError(Exception):
    pass


class ImagePreparationService:
    def __init__(self, immich_client: Optional[ImmichClient] = None):
        self.immich_client = immich_client or ImmichClient()
        self.max_bytes = settings.MAX_IMAGE_BYTES
        self.target_size: Tuple[int, int] = settings.thumbnail_size

    def prepare_for_provider(
        self,
        asset_id: str,
        size: str = "thumbnail",
    ) -> dict:
        """
        Fetch and prepare image for AI provider.
        Returns: {"data_url": str, "mime_type": str, "size_bytes": int}
        """
        try:
            image_bytes = self.immich_client.get_thumbnail(asset_id, size=size)
        except ImmichError as e:
            raise ImagePreparationError(f"Could not fetch thumbnail: {e}")

        if len(image_bytes) > self.max_bytes:
            raise ImagePreparationError(
                f"Image too large: {len(image_bytes)} bytes (max {self.max_bytes})"
            )

        mime_type, processed_bytes = self._process_image(image_bytes)

        data_url = self._to_data_url(processed_bytes, mime_type)

        return {
            "data_url": data_url,
            "mime_type": mime_type,
            "size_bytes": len(processed_bytes),
        }

    def _process_image(self, image_bytes: bytes) -> Tuple[str, bytes]:
        """Detect mime type and resize if needed. Returns (mime_type, bytes)."""
        if not PIL_AVAILABLE:
            # Fallback: assume jpeg if Pillow not available
            return "image/jpeg", image_bytes

        try:
            img = Image.open(io.BytesIO(image_bytes))
            fmt = (img.format or "JPEG").upper()
            mime_type = f"image/{fmt.lower()}"
            if mime_type not in ALLOWED_MIME_TYPES:
                mime_type = "image/jpeg"
                fmt = "JPEG"

            # Convert palette/RGBA to RGB for JPEG compatibility
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
                mime_type = "image/jpeg"
                fmt = "JPEG"

            # Resize if larger than target
            if img.width > self.target_size[0] or img.height > self.target_size[1]:
                img.thumbnail(self.target_size, Image.LANCZOS)

            buf = io.BytesIO()
            save_fmt = "JPEG" if fmt not in {"PNG", "GIF", "WEBP"} else fmt
            # Keep MIME type in sync with the actual saved format
            mime_type = f"image/{save_fmt.lower()}"
            img.save(buf, format=save_fmt, quality=85)
            return mime_type, buf.getvalue()

        except Exception as e:
            raise ImagePreparationError(f"Image processing failed: {e}")

    def _to_data_url(self, image_bytes: bytes, mime_type: str) -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{b64}"
