"""GeoID resolver -- translates AgStack GeoIDs to coordinates.

Grant-aware: by default the resolver reads the masked L0 centroid (no grant
needed). When a field grant is supplied it is forwarded as ``X-Field-Grant`` and
the exact L1 boundary (WKT) can additionally be fetched -- e.g. for sub-field
zoning. This mirrors the AR2 masking model (L0 default, L1 on consent).
"""

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
        field_grant: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._field_grant = field_grant

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._field_grant:
            headers["X-Field-Grant"] = self._field_grant
        return headers

    async def resolve(self, geo_id: str, *, fetch_wkt: bool = False) -> FieldLocation:
        """Resolve a GeoID to a FieldLocation via the Asset Registry API.

        Calls ``GET /fetch-field-centroid/{geo_id}`` for the (L0) centroid. When
        ``fetch_wkt`` is set and a field grant was provided, also calls
        ``GET /fetch-field-wkt/{geo_id}`` for the exact (L1) boundary.
        """
        headers = self._headers()

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

            wkt: str | None = None
            if fetch_wkt and self._field_grant:
                wkt = await self._fetch_wkt(client, geo_id, headers)

            return FieldLocation(
                latitude=float(centroid[0]),
                longitude=float(centroid[1]),
                geo_id=geo_id,
                wkt=wkt,
            )

    async def _fetch_wkt(
        self, client: httpx.AsyncClient, geo_id: str, headers: dict[str, str]
    ) -> str | None:
        """Fetch the exact L1 boundary WKT; returns None if not authorized."""
        try:
            resp = await client.get(
                f"{self._base_url}/fetch-field-wkt/{geo_id}", headers=headers
            )
        except httpx.HTTPError as exc:
            raise GeoResolverError(f"Network error fetching WKT: {exc}") from exc
        if resp.status_code in (401, 403):
            # No/insufficient grant: silently stay at L0 (centroid only).
            return None
        if resp.status_code != 200:
            raise GeoResolverError(
                f"Asset Registry WKT returned {resp.status_code}: {resp.text}"
            )
        data = resp.json()
        return data.get("wkt") or data.get("WKT")

    @staticmethod
    def from_coordinates(latitude: float, longitude: float) -> FieldLocation:
        """Create a FieldLocation directly from raw coordinates (no GeoID)."""
        return FieldLocation(latitude=latitude, longitude=longitude)
