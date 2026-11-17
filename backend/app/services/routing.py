import logging
import math
from collections.abc import Mapping, Sequence
from typing import Literal

import httpx

from app.core.config import settings
from app.schemas.routing import RouteCoordinate, RouteGeometry, RouteResponse
from app.services.geography import validate_coordinate
from app.services.providers import GeographicProviderError, response_json

logger = logging.getLogger(__name__)

RouteMode = Literal["car", "bike", "walk"]
ROUTE_PROFILES: dict[RouteMode, str] = {
    "car": "driving-car",
    "bike": "driving-car",
    "walk": "foot-walking",
}


class RoutingConfigurationError(RuntimeError):
    pass


class OpenRouteServiceClient:
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        configured_key = (
            settings.openrouteservice_api_key.get_secret_value()
            if settings.openrouteservice_api_key is not None
            else None
        )
        self._api_key = (api_key if api_key is not None else configured_key or "").strip()
        self._client = client

    async def route(
        self,
        origin: RouteCoordinate,
        destination: RouteCoordinate,
        mode: RouteMode,
    ) -> RouteResponse:
        if not self._api_key:
            raise RoutingConfigurationError("OpenRouteService API key is not configured")
        validate_coordinate(origin.longitude, origin.latitude)
        validate_coordinate(destination.longitude, destination.latitude)

        profile = ROUTE_PROFILES[mode]
        url = f"{settings.openrouteservice_directions_url}/{profile}/geojson"
        headers = {"Authorization": self._api_key}
        payload = {
            "coordinates": [
                [origin.longitude, origin.latitude],
                [destination.longitude, destination.latitude],
            ]
        }
        response = await self._post(url, headers, payload)
        return self._normalize_response(response)

    async def _post(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> httpx.Response:
        try:
            if self._client is not None:
                response = await self._client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
            else:
                async with httpx.AsyncClient(
                    timeout=settings.provider_timeout_seconds
                ) as client:
                    response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            response = getattr(exc, "response", None)
            logger.warning("OpenRouteService request failed: %s", exc)
            raise GeographicProviderError(
                "OpenRouteService",
                str(exc),
                status_code=response.status_code if response is not None else None,
                retry_after=(
                    response.headers.get("Retry-After")
                    if response is not None
                    else None
                ),
            ) from exc

    @staticmethod
    def _normalize_response(response: httpx.Response) -> RouteResponse:
        payload = response_json("OpenRouteService", response)
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise GeographicProviderError(
                "OpenRouteService", "response has no route features"
            )
        feature = features[0]
        if not isinstance(feature, Mapping):
            raise GeographicProviderError(
                "OpenRouteService", "route feature is invalid"
            )
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if (
            not isinstance(geometry, Mapping)
            or geometry.get("type") != "LineString"
            or not isinstance(properties, Mapping)
        ):
            raise GeographicProviderError(
                "OpenRouteService", "route feature is missing geometry or summary"
            )

        raw_coordinates = geometry.get("coordinates")
        summary = properties.get("summary")
        if (
            not isinstance(raw_coordinates, Sequence)
            or isinstance(raw_coordinates, (str, bytes))
            or not isinstance(summary, Mapping)
            or len(raw_coordinates) < 2
        ):
            raise GeographicProviderError(
                "OpenRouteService", "route geometry or summary is invalid"
            )
        coordinates: list[tuple[float, float]] = []
        for coordinate in raw_coordinates:
            if (
                not isinstance(coordinate, Sequence)
                or isinstance(coordinate, (str, bytes))
                or len(coordinate) < 2
            ):
                raise GeographicProviderError(
                    "OpenRouteService", "route contains an invalid coordinate"
                )
            try:
                longitude, latitude = validate_coordinate(
                    coordinate[0], coordinate[1]
                )
            except ValueError as exc:
                raise GeographicProviderError(
                    "OpenRouteService", "route contains an invalid coordinate"
                ) from exc
            coordinates.append((longitude, latitude))

        distance = OpenRouteServiceClient._nonnegative_number(
            summary.get("distance"), "distance"
        )
        duration = OpenRouteServiceClient._nonnegative_number(
            summary.get("duration"), "duration"
        )
        return RouteResponse(
            geometry=RouteGeometry(coordinates=coordinates),
            distance_meters=distance,
            duration_seconds=duration,
        )

    @staticmethod
    def _nonnegative_number(value: object, field: str) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise GeographicProviderError(
                "OpenRouteService", f"route summary has invalid {field}"
            )
        return float(value)


routing_client = OpenRouteServiceClient()
