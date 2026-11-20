"""Transient Google Places lookups for destinations and nearby parking."""

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.services.geography import validate_coordinate
from app.services.parking_normalization import NormalizedParking
from app.services.providers import GeographicProviderError, response_json


@dataclass(frozen=True, slots=True)
class GooglePlace:
    place_id: str
    name: str
    address: str | None
    latitude: float
    longitude: float
    types: tuple[str, ...]


class GooglePlacesClient:
    _base_url = "https://places.googleapis.com/v1/places"
    _field_mask = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.location,places.types"
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search_destinations(
        self,
        query: str,
        limit: int = 5,
        bias: tuple[float, float] | None = None,
    ) -> tuple[GooglePlace, ...]:
        query = " ".join(query.split())
        if not query or not 1 <= limit <= 20:
            raise ValueError("Provide a query and a limit between 1 and 20")
        body: dict[str, Any] = {
            "textQuery": query,
            "maxResultCount": limit,
            "regionCode": "PK",
        }
        if bias is not None:
            latitude, longitude = bias
            validate_coordinate(longitude, latitude)
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": 50_000.0,
                }
            }
        return await self._search("searchText", body)

    async def nearby_parking(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 2000,
        limit: int = 20,
    ) -> tuple[NormalizedParking, ...]:
        validate_coordinate(longitude, latitude)
        if not 100 <= radius_meters <= 50_000 or not 1 <= limit <= 20:
            raise ValueError("Parking radius or result limit is outside the supported range")
        body = {
            "includedTypes": ["parking"],
            "maxResultCount": limit,
            "rankPreference": "DISTANCE",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius_meters),
                }
            },
        }
        places = await self._search("searchNearby", body)
        return tuple(
            NormalizedParking(
                osm_id=f"google/{place.place_id}",
                name=place.name,
                geometry={
                    "type": "Point",
                    "coordinates": [place.longitude, place.latitude],
                },
                parking_type="parking",
                fee=None,
                capacity=None,
                access=None,
                supports_car=None,
                supports_bike=None,
                tags={"addr:full": place.address} if place.address else {},
                source="google_maps",
            )
            for place in places
        )

    async def _search(
        self, method: str, body: dict[str, Any]
    ) -> tuple[GooglePlace, ...]:
        secret = settings.google_maps_api_key
        if secret is None or not secret.get_secret_value():
            raise GeographicProviderError("Google Places", "API key is not configured", 503)
        headers = {
            "X-Goog-Api-Key": secret.get_secret_value(),
            "X-Goog-FieldMask": self._field_mask,
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self._base_url}:{method}", json=body, headers=headers
                )
            else:
                async with httpx.AsyncClient(
                    timeout=settings.provider_timeout_seconds
                ) as client:
                    response = await client.post(
                        f"{self._base_url}:{method}", json=body, headers=headers
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            failed_response = getattr(exc, "response", None)
            raise GeographicProviderError(
                "Google Places",
                "request failed",
                status_code=(
                    failed_response.status_code if failed_response is not None else None
                ),
                retry_after=(
                    failed_response.headers.get("Retry-After")
                    if failed_response is not None
                    else None
                ),
            ) from exc

        payload = response_json("Google Places", response)
        raw_places = payload.get("places", [])
        if not isinstance(raw_places, list):
            raise GeographicProviderError("Google Places", "invalid places response")
        places: list[GooglePlace] = []
        for raw in raw_places:
            place = self._normalize(raw)
            if place is not None:
                places.append(place)
        return tuple(places)

    @staticmethod
    def _normalize(raw: object) -> GooglePlace | None:
        if not isinstance(raw, dict):
            return None
        place_id = raw.get("id")
        display_name = raw.get("displayName")
        location = raw.get("location")
        if (
            not isinstance(place_id, str)
            or not isinstance(display_name, dict)
            or not isinstance(location, dict)
        ):
            return None
        name = display_name.get("text")
        if not isinstance(name, str) or not name.strip():
            return None
        try:
            longitude, latitude = validate_coordinate(
                location.get("longitude"), location.get("latitude")
            )
        except ValueError:
            return None
        address = raw.get("formattedAddress")
        raw_types = raw.get("types")
        return GooglePlace(
            place_id=place_id,
            name=name.strip(),
            address=address if isinstance(address, str) else None,
            latitude=latitude,
            longitude=longitude,
            types=tuple(value for value in raw_types if isinstance(value, str))
            if isinstance(raw_types, list)
            else (),
        )
