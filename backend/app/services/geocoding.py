import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.services.cache import TTLCache
from app.services.geography import validate_coordinate
from app.services.providers import GeographicProviderError, response_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DestinationCandidate:
    name: str
    category: str | None
    address: str | None
    latitude: float
    longitude: float
    osm_id: str | None


class PhotonGeocoder:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        cache: TTLCache[str, tuple[DestinationCandidate, ...]] | None = None,
    ) -> None:
        self._client = client
        self._cache = cache or TTLCache(settings.geodata_cache_ttl_seconds)

    async def search(
        self,
        query: str,
        limit: int = 5,
        bias: tuple[float, float] | None = None,
    ) -> tuple[DestinationCandidate, ...]:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("Destination search query cannot be empty")
        if not 1 <= limit <= 10:
            raise ValueError("Geocoding result limit must be between 1 and 10")

        bias_key = (
            f"{bias[0]:.5f},{bias[1]:.5f}" if bias is not None else "unbiased"
        )
        cache_key = f"{normalized_query.casefold()}|{limit}|{bias_key}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {"q": normalized_query, "limit": limit}
        if bias is not None:
            latitude, longitude = bias
            validate_coordinate(longitude, latitude)
            params.update({"lat": latitude, "lon": longitude})

        response = await self._get(params)
        payload = response_json("Photon", response)
        features = payload.get("features")
        if not isinstance(features, list):
            raise GeographicProviderError("Photon", "response has no feature list")

        candidates: list[DestinationCandidate] = []
        seen_ids: set[str] = set()
        for feature in features:
            candidate = self._normalize_feature(feature)
            if candidate is None:
                continue
            if candidate.osm_id is not None and candidate.osm_id in seen_ids:
                continue
            if candidate.osm_id is not None:
                seen_ids.add(candidate.osm_id)
            candidates.append(candidate)

        result = tuple(candidates)
        self._cache.set(cache_key, result)
        return result

    async def _get(self, params: dict[str, Any]) -> httpx.Response:
        headers = {"User-Agent": settings.provider_user_agent}
        try:
            if self._client is not None:
                response = await self._client.get(
                    settings.photon_url, params=params, headers=headers
                )
            else:
                async with httpx.AsyncClient(
                    timeout=settings.provider_timeout_seconds
                ) as client:
                    response = await client.get(
                        settings.photon_url, params=params, headers=headers
                    )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            response = getattr(exc, "response", None)
            logger.warning("Photon request failed: %s", exc)
            raise GeographicProviderError(
                "Photon",
                str(exc),
                status_code=response.status_code if response is not None else None,
                retry_after=response.headers.get("Retry-After") if response is not None else None,
            ) from exc

    @staticmethod
    def _normalize_feature(feature: object) -> DestinationCandidate | None:
        if not isinstance(feature, dict):
            logger.warning("Skipping invalid Photon feature")
            return None
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            logger.warning("Skipping Photon feature without properties or geometry")
            return None

        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not isinstance(coordinates, list) or len(coordinates) != 2:
            logger.warning("Skipping Photon feature with invalid point geometry")
            return None
        try:
            longitude, latitude = validate_coordinate(coordinates[0], coordinates[1])
        except ValueError:
            logger.warning("Skipping Photon feature with invalid coordinates")
            return None

        name = properties.get("name") or properties.get("street")
        if not isinstance(name, str) or not name.strip():
            logger.warning("Skipping Photon feature without a usable name")
            return None

        address_parts = [
            properties.get(key)
            for key in ("housenumber", "street", "district", "city", "state", "country")
        ]
        address = ", ".join(
            dict.fromkeys(part.strip() for part in address_parts if isinstance(part, str) and part.strip())
        ) or None

        osm_type = properties.get("osm_type")
        osm_value = properties.get("osm_id")
        osm_id = (
            f"{osm_type}/{osm_value}"
            if isinstance(osm_type, str)
            and not isinstance(osm_value, bool)
            and isinstance(osm_value, (str, int))
            else None
        )
        category = properties.get("type") or properties.get("osm_value")
        return DestinationCandidate(
            name=name.strip(),
            category=category if isinstance(category, str) else None,
            address=address,
            latitude=latitude,
            longitude=longitude,
            osm_id=osm_id,
        )


geocoder = PhotonGeocoder()
