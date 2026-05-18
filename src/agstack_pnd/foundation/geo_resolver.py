"""GeoID resolver -- translates AgStack GeoIDs to coordinates."""

from __future__ import annotations

import httpx

from agstack_pnd.foundation.exceptions import GeoIDNotFound, GeoResolverError
from agstack_pnd.foundation.types import FieldLocation

ASSET_REGISTRY_BASE = "https://api-ar.agstack.org"


class GeoResolver:
    """Resolves AgStack GeoIDs to lat/lon coordinates.

    Falls back to raw lat/lon when no GeoID is provided.
    """

    def __init__(
        self,
        base_url: str = ASSET_REGISTRY_BASE,
        token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    async def resolve(self, geo_id: str) -> FieldLocation:
        """Resolve a GeoID to a FieldLocation via the Asset Registry API.

        Calls ``GET /fetch-field-centroid/{geo_id}`` to obtain coordinates,
        and optionally ``GET /fetch-field-wkt/{geo_id}`` for the full boundary.
        """
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/fetch-field-centroid/{geo_id}",
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                raise GeoResolverError(f"Network error resolving GeoID: {exc}") from exc

            if resp.status_code == 404:
                raise GeoIDNotFound(geo_id)
            if resp.status_code != 200:
                raise GeoResolverError(
                    f"Asset Registry returned {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            centroid = data.get("centroid") or data.get("Centroid")
            if not centroid or len(centroid) < 2:
                raise GeoResolverError(f"Invalid centroid response for GeoID '{geo_id}'")

            return FieldLocation(
                latitude=float(centroid[0]),
                longitude=float(centroid[1]),
                geo_id=geo_id,
            )

    @staticmethod
    def from_coordinates(latitude: float, longitude: float) -> FieldLocation:
        """Create a FieldLocation directly from raw coordinates (no GeoID)."""
        return FieldLocation(latitude=latitude, longitude=longitude)
