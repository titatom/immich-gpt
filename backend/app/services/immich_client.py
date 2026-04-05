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
        is_favorite: Optional[bool] = None,
        is_archived: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List assets with pagination.

        Newer Immich versions (≥ v1.106) removed GET /api/assets in favour of
        POST /api/search/metadata (renamed POST /api/search/assets in v1.118+).
        We try the search endpoint first, then fall back to the legacy GET.
        """
        body: Dict[str, Any] = {
            "page": page,
            "size": page_size,
            "withExif": True,
            "withArchived": True,
        }
        if asset_type:
            body["type"] = asset_type
        if is_favorite is not None:
            body["isFavorite"] = is_favorite
        if is_archived is not None:
            body["isArchived"] = is_archived

        with self._client() as client:
            # Try POST /api/search/metadata (v1.106–v1.117)
            r = client.post("/api/search/metadata", json=body)
            if r.status_code == 404:
                # Try POST /api/search/assets (v1.118+)
                r = client.post("/api/search/assets", json=body)
            if r.status_code == 404:
                # Fall back to legacy GET /api/assets (pre-v1.106)
                params: Dict[str, Any] = {"page": page, "size": page_size, "withExif": True}
                if asset_type:
                    params["type"] = asset_type
                if is_favorite is not None:
                    params["isFavorite"] = is_favorite
                if is_archived is not None:
                    params["isArchived"] = is_archived
                r = client.get("/api/assets", params=params)
                if r.status_code != 200:
                    raise ImmichError(f"Failed to list assets: {r.text}", r.status_code)
                data = r.json()
                # Legacy endpoint returns a plain list
                return data if isinstance(data, list) else []

            if r.status_code != 200:
                raise ImmichError(f"Failed to list assets: {r.text}", r.status_code)

            data = r.json()
            # Search endpoints return { items: [...], total: N } or { assets: { items: [...] } }
            if isinstance(data, dict):
                items = data.get("items") or data.get("assets", {}).get("items", [])
                return items if isinstance(items, list) else []
            return data if isinstance(data, list) else []

    def list_album_assets(
        self,
        album_id: str,
        page: int = 1,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """List assets in a specific album with pagination."""
        with self._client() as client:
            r = client.get(f"/api/albums/{album_id}", params={"withoutAssets": False})
            if r.status_code != 200:
                raise ImmichError(f"Failed to get album {album_id}: {r.text}", r.status_code)
            data = r.json()
            assets = data.get("assets", [])
            # Return paginated slice
            start = (page - 1) * page_size
            return assets[start : start + page_size]

    def get_album_asset_count(self, album_id: str) -> int:
        """Get asset count for a specific album."""
        with self._client() as client:
            r = client.get(f"/api/albums/{album_id}", params={"withoutAssets": True})
            if r.status_code != 200:
                raise ImmichError(f"Failed to get album {album_id}: {r.text}", r.status_code)
            return r.json().get("assetCount", 0)

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

    def get_existing_tags_only(self, tag_names: List[str]) -> List[Dict[str, Any]]:
        """
        Return only tags that already exist in Immich — never creates new ones.
        Silently skips tag names not found.
        """
        with self._client() as client:
            r = client.get("/api/tags")
            existing: Dict[str, Dict[str, Any]] = {}
            if r.status_code == 200:
                for t in r.json():
                    existing[t.get("name", "").lower()] = t

            return [existing[name.lower()] for name in tag_names if name.lower() in existing]

    def get_existing_album(self, album_name: str) -> Optional[Dict[str, Any]]:
        """Return an existing album by name, or None if it doesn't exist. Never creates."""
        with self._client() as client:
            r = client.get("/api/albums")
            if r.status_code == 200:
                for album in r.json():
                    if album.get("albumName", "").lower() == album_name.lower():
                        return album
        return None

    def get_or_create_tags(self, tag_names: List[str]) -> List[Dict[str, Any]]:
        """
        Batch-resolve tag names to Immich tag objects, creating missing ones.

        Fetches the full tag list once per call to minimise round-trips.
        Returns a list of tag dicts (with at least {"id": ..., "name": ...}).
        """
        with self._client() as client:
            r = client.get("/api/tags")
            existing: Dict[str, Dict[str, Any]] = {}
            if r.status_code == 200:
                for t in r.json():
                    existing[t.get("name", "").lower()] = t

            result: List[Dict[str, Any]] = []
            for name in tag_names:
                lower = name.lower()
                if lower in existing:
                    result.append(existing[lower])
                else:
                    cr = client.post("/api/tags", json={"name": name})
                    if cr.status_code in (200, 201):
                        tag = cr.json()
                        existing[lower] = tag
                        result.append(tag)
                    else:
                        raise ImmichError(f"Failed to create tag '{name}': {cr.text}")
            return result

    # Keep old single-tag helper as a thin wrapper for backwards compat
    def get_or_create_tag(self, tag_name: str) -> Dict[str, Any]:
        """Get existing tag or create new one in Immich. Single-tag convenience wrapper."""
        results = self.get_or_create_tags([tag_name])
        return results[0]

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

    def get_or_create_album(self, album_name: str) -> Dict[str, Any]:
        """
        Return an existing Immich album by name, or create it.
        Used for subalbum write-back when no explicit immich_album_id is set.
        """
        with self._client() as client:
            r = client.get("/api/albums")
            if r.status_code == 200:
                for album in r.json():
                    if album.get("albumName", "").lower() == album_name.lower():
                        return album
            # Create
            cr = client.post("/api/albums", json={"albumName": album_name})
            if cr.status_code not in (200, 201):
                raise ImmichError(f"Failed to create album '{album_name}': {cr.text}")
            return cr.json()

    def is_external_library_asset(self, asset: Dict[str, Any]) -> bool:
        """Detect if asset is from an external library (may restrict writes)."""
        lib = asset.get("library", {}) or {}
        return lib.get("type", "") == "EXTERNAL"
