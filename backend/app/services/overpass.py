import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.cache import TTLCache
from app.services.parking_normalization import NormalizedParking, normalize_parking_elements
from app.services.road_network_normalization import (
    NormalizedRoadNetwork,
    normalize_road_network_elements,
)
from app.services.providers import GeographicProviderError, response_json

logger = logging.getLogger(__name__)
PARKING_AMENITIES = (
    "parking",
    "motorcycle_parking",
    "parking_entrance",
    "parking_space",
)


class OverpassClient:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        cache: TTLCache[str, tuple[NormalizedParking, ...]] | None = None,
    ) -> None:
        self._client = client
        self._cache = cache or TTLCache(settings.geodata_cache_ttl_seconds)
        self._road_cache: TTLCache[str, NormalizedRoadNetwork] = TTLCache(
            settings.geodata_cache_ttl_seconds
        )

    async def nearby_parking(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1500,
    ) -> tuple[NormalizedParking, ...]:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordinates are outside valid longitude/latitude bounds")
        if not 100 <= radius_meters <= 50000:
            raise ValueError("Parking search radius must be between 100 and 50000 meters")

        cache_key = f"{latitude:.5f},{longitude:.5f},{radius_meters}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        query = self._query(latitude, longitude, radius_meters)
        response = await self._post({"data": query})
        payload = response_json("Overpass", response)
        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise GeographicProviderError("Overpass", "response has no elements list")

        results = normalize_parking_elements(elements)
        self._cache.set(cache_key, results)
        return results

    async def roads_within(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1500,
    ) -> NormalizedRoadNetwork:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Coordinates are outside valid longitude/latitude bounds")
        if not 100 <= radius_meters <= 5000:
            raise ValueError("Road search radius must be between 100 and 5000 meters")

        cache_key = f"{latitude:.6f},{longitude:.6f},{radius_meters}"
        cached = self._road_cache.get(cache_key)
        if cached is not None:
            return cached

        response = await self._post(
            {"data": self._road_query(latitude, longitude, radius_meters)},
            timeout_seconds=settings.road_network_timeout_seconds,
        )
        payload = response_json("Overpass", response)
        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise GeographicProviderError("Overpass", "response has no elements list")
        try:
            network = normalize_road_network_elements(
                elements,
                center_latitude=latitude,
                center_longitude=longitude,
                radius_meters=radius_meters,
            )
        except ValueError as exc:
            raise GeographicProviderError(
                "Overpass", "response has invalid road network data"
            ) from exc

        self._road_cache.set(cache_key, network)
        return network

    @staticmethod
    def _query(latitude: float, longitude: float, radius_meters: int) -> str:
        tags = f'"amenity"~"^({"|".join(PARKING_AMENITIES)})$"'
        selectors = "\n".join(
            f'{element_type}[{tags}](around:{radius_meters},{latitude:.6f},{longitude:.6f});'
            for element_type in ("node", "way", "relation")
        )
        return f"[out:json][timeout:25];\n(\n{selectors}\n);\nout center geom;"

    @staticmethod
    def _road_query(latitude: float, longitude: float, radius_meters: int) -> str:
        return (
            f"[out:json][timeout:{settings.road_network_timeout_seconds}];\n"
            f'way(around:{radius_meters},{latitude:.6f},{longitude:.6f})["highway"];\n'
            "out body geom;"
        )

    async def _post(
        self,
        data: dict[str, Any],
        timeout_seconds: float | None = None,
    ) -> httpx.Response:
        headers = {"User-Agent": settings.provider_user_agent}
        try:
            if self._client is not None:
                response = await self._client.post(
                    settings.overpass_url, data=data, headers=headers
                )
            else:
                async with httpx.AsyncClient(
                    timeout=timeout_seconds or settings.provider_timeout_seconds
                ) as client:
                    response = await client.post(
                        settings.overpass_url, data=data, headers=headers
                    )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            response = getattr(exc, "response", None)
            logger.warning("Overpass request failed: %s", exc)
            raise GeographicProviderError(
                "Overpass",
                str(exc),
                status_code=response.status_code if response is not None else None,
                retry_after=response.headers.get("Retry-After") if response is not None else None,
            ) from exc


overpass_client = OverpassClient()
