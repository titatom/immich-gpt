"""
ImmichClient: all Immich API communication.
All Immich HTTP calls are isolated here.
"""
import httpx
from typing import Optional, List, Dict, Any
from ..config import settings


class ImmichError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ImmichClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.IMMICH_URL).rstrip("/")
        self.api_key = api_key or settings.IMMICH_API_KEY
        self._headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers=self._headers,
            timeout=30,
        )

    def check_connectivity(self) -> Dict[str, Any]:
        """Check if Immich is reachable and credentials are valid."""
        try:
            with self._client() as client:
                r = client.get("/api/server/ping")
                if r.status_code == 200:
                    info = client.get("/api/server/about")
                    return {"connected": True, "info": info.json() if info.status_code == 200 else {}}
                raise ImmichError("Immich ping failed", r.status_code)
        except httpx.ConnectError as e:
            raise ImmichError(f"Cannot connect to Immich: {e}")
        except httpx.TimeoutException:
            raise ImmichError("Connection to Immich timed out")

    def get_asset_count(self) -> int:
        with self._client() as client:
            r = client.get("/api/assets/statistics")
            r.raise_for_status()
            data = r.json()
            return data.get("total", 0)

    def list_assets(
        self,
        page: int = 1,
        page_size: int = 100,
        asset_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List assets with pagination."""
        params: Dict[str, Any] = {"page": page, "size": page_size, "withExif": True}
        if asset_type:
            params["type"] = asset_type
        with self._client() as client:
            r = client.get("/api/assets", params=params)
            if r.status_code != 200:
                raise ImmichError(f"Failed to list assets: {r.text}", r.status_code)
            return r.json()

    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Get full asset metadata."""
        with self._client() as client:
            r = client.get(f"/api/assets/{asset_id}")
            if r.status_code != 200:
                raise ImmichError(f"Asset {asset_id} not found", r.status_code)
            return r.json()

    def get_thumbnail(self, asset_id: str, size: str = "thumbnail") -> bytes:
        """
        Fetch asset thumbnail bytes.
        size: "thumbnail" or "preview"
        Never returns a private URL to external callers.
        """
        with self._client() as client:
            r = client.get(
                f"/api/assets/{asset_id}/thumbnail",
                params={"size": size},
                headers={**self._headers, "Accept": "image/*"},
            )
            if r.status_code != 200:
                raise ImmichError(
                    f"Thumbnail unavailable for {asset_id}", r.status_code
                )
            return r.content

    def list_albums(self) -> List[Dict[str, Any]]:
        with self._client() as client:
            r = client.get("/api/albums")
            r.raise_for_status()
            return r.json()

    def add_asset_to_album(self, album_id: str, asset_ids: List[str]) -> Dict[str, Any]:
        with self._client() as client:
            r = client.put(
                f"/api/albums/{album_id}/assets",
                json={"ids": asset_ids},
            )
            if r.status_code not in (200, 201):
                raise ImmichError(
                    f"Failed to add asset to album {album_id}: {r.text}",
                    r.status_code,
                )
            return r.json()

    def update_asset_description(self, asset_id: str, description: str) -> Dict[str, Any]:
        """Write description (exif info) back to Immich."""
        with self._client() as client:
            r = client.put(
                f"/api/assets/{asset_id}",
                json={"description": description},
            )
            if r.status_code not in (200, 201):
                raise ImmichError(
                    f"Failed to update description for {asset_id}: {r.text}",
                    r.status_code,
                )
            return r.json()

    def get_or_create_tag(self, tag_name: str) -> Dict[str, Any]:
        """Get existing tag or create new one in Immich."""
        with self._client() as client:
            # Try to find existing tag
            r = client.get("/api/tags")
            if r.status_code == 200:
                tags = r.json()
                for tag in tags:
                    if tag.get("name", "").lower() == tag_name.lower():
                        return tag

            # Create tag
            r = client.post("/api/tags", json={"name": tag_name})
            if r.status_code not in (200, 201):
                raise ImmichError(f"Failed to create tag '{tag_name}': {r.text}")
            return r.json()

    def tag_asset(self, asset_id: str, tag_ids: List[str]) -> None:
        """Apply tags to an asset."""
        with self._client() as client:
            r = client.put(
                "/api/tags/assets",
                json={"assetIds": [asset_id], "tagIds": tag_ids},
            )
            if r.status_code not in (200, 201):
                raise ImmichError(
                    f"Failed to tag asset {asset_id}: {r.text}", r.status_code
                )

    def is_external_library_asset(self, asset: Dict[str, Any]) -> bool:
        """Detect if asset is from an external library (may restrict writes)."""
        lib = asset.get("library", {}) or {}
        return lib.get("type", "") == "EXTERNAL"
