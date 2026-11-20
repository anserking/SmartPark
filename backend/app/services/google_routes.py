"""Google Routes API adapter for the dashboard's drive and walk journey."""

import math
from collections.abc import Mapping

import httpx

from app.core.config import settings
from app.schemas.routing import RouteCoordinate, RouteGeometry, RouteResponse
from app.services.geography import validate_coordinate
from app.services.providers import GeographicProviderError, response_json
from app.services.routing import RouteMode, RoutingConfigurationError


class GoogleRoutesClient:
    _url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    _field_mask = "routes.duration,routes.distanceMeters,routes.polyline.geoJsonLinestring"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def route(
        self, origin: RouteCoordinate, destination: RouteCoordinate, mode: RouteMode
    ) -> RouteResponse:
        secret = settings.google_maps_api_key
        if secret is None or not secret.get_secret_value():
            raise RoutingConfigurationError("Google Maps API key is not configured")
        validate_coordinate(origin.longitude, origin.latitude)
        validate_coordinate(destination.longitude, destination.latitude)
        # The former bike journey used a car profile; keep that behavior until
        # two-wheeler coverage is verified for every supported destination.
        travel_mode = "WALK" if mode == "walk" else "DRIVE"
        body = {
            "origin": {"location": {"latLng": {
                "latitude": origin.latitude, "longitude": origin.longitude,
            }}},
            "destination": {"location": {"latLng": {
                "latitude": destination.latitude, "longitude": destination.longitude,
            }}},
            "travelMode": travel_mode,
            "polylineEncoding": "GEO_JSON_LINESTRING",
        }
        headers = {
            "X-Goog-Api-Key": secret.get_secret_value(),
            "X-Goog-FieldMask": self._field_mask,
        }
        try:
            if self._client is not None:
                response = await self._client.post(self._url, json=body, headers=headers)
            else:
                async with httpx.AsyncClient(
                    timeout=settings.provider_timeout_seconds
                ) as client:
                    response = await client.post(self._url, json=body, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            failed_response = getattr(exc, "response", None)
            raise GeographicProviderError(
                "Google Routes", "request failed",
                status_code=(failed_response.status_code if failed_response is not None else None),
                retry_after=(failed_response.headers.get("Retry-After") if failed_response is not None else None),
            ) from exc

        payload = response_json("Google Routes", response)
        routes = payload.get("routes")
        if not isinstance(routes, list) or not routes or not isinstance(routes[0], Mapping):
            raise GeographicProviderError("Google Routes", "response has no routes")
        route = routes[0]
        polyline = route.get("polyline")
        geometry = polyline.get("geoJsonLinestring") if isinstance(polyline, Mapping) else None
        coordinates = geometry.get("coordinates") if isinstance(geometry, Mapping) else None
        if (
            not isinstance(geometry, Mapping)
            or geometry.get("type") != "LineString"
            or not isinstance(coordinates, list)
            or len(coordinates) < 2
        ):
            raise GeographicProviderError("Google Routes", "route geometry is invalid")
        points = []
        for item in coordinates:
            if not isinstance(item, list) or len(item) != 2:
                raise GeographicProviderError("Google Routes", "route coordinate is invalid")
            try:
                points.append(tuple(validate_coordinate(item[0], item[1])))
            except ValueError as exc:
                raise GeographicProviderError("Google Routes", "route coordinate is invalid") from exc
        distance = route.get("distanceMeters")
        duration = route.get("duration")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or not math.isfinite(distance) or distance < 0:
            raise GeographicProviderError("Google Routes", "route distance is invalid")
        if not isinstance(duration, str) or not duration.endswith("s"):
            raise GeographicProviderError("Google Routes", "route duration is invalid")
        try:
            duration_seconds = float(duration[:-1])
        except ValueError as exc:
            raise GeographicProviderError("Google Routes", "route duration is invalid") from exc
        if not math.isfinite(duration_seconds) or duration_seconds < 0:
            raise GeographicProviderError("Google Routes", "route duration is invalid")
        return RouteResponse(
            geometry=RouteGeometry(coordinates=points),
            distance_meters=float(distance),
            duration_seconds=duration_seconds,
        )


google_routes_client = GoogleRoutesClient()
