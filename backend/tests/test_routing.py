import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_routing_client
from app.main import app
from app.schemas.routing import RouteCoordinate, RouteGeometry, RouteResponse
from app.services.providers import GeographicProviderError
from app.services.routing import (
    OpenRouteServiceClient,
    RouteMode,
    RoutingConfigurationError,
)

ROUTE_PAYLOAD = {
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[67.01, 24.86], [67.02, 24.87]],
            },
            "properties": {
                "summary": {"distance": 1450.5, "duration": 420.25},
            },
        }
    ]
}


@pytest.mark.parametrize(
    ("mode", "profile"),
    [
        ("car", "driving-car"),
        ("bike", "driving-car"),
        ("walk", "foot-walking"),
    ],
)
def test_openrouteservice_uses_private_key_and_normalizes_route(
    mode: RouteMode,
    profile: str,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=ROUTE_PAYLOAD)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            routing = OpenRouteServiceClient(api_key="test-secret", client=client)
            return await routing.route(
                RouteCoordinate(latitude=24.86, longitude=67.01),
                RouteCoordinate(latitude=24.87, longitude=67.02),
                mode,
            )

    result = asyncio.run(run())
    request = requests[0]

    assert request.url.path.endswith(f"/{profile}/geojson")
    assert request.headers["Authorization"] == "test-secret"
    assert json.loads(request.read()) == {
        "coordinates": [[67.01, 24.86], [67.02, 24.87]]
    }
    assert result.geometry.type == "LineString"
    assert result.geometry.coordinates == [(67.01, 24.86), (67.02, 24.87)]
    assert result.distance_meters == 1450.5
    assert result.duration_seconds == 420.25


def test_openrouteservice_requires_a_configured_key() -> None:
    routing = OpenRouteServiceClient(api_key="")

    async def run() -> None:
        await routing.route(
            RouteCoordinate(latitude=24.86, longitude=67.01),
            RouteCoordinate(latitude=24.87, longitude=67.02),
            "car",
        )

    with pytest.raises(RoutingConfigurationError):
        asyncio.run(run())


def test_openrouteservice_rejects_malformed_route_geometry() -> None:
    payload = {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [67.01, 24.86]},
                "properties": {"summary": {"distance": 10, "duration": 5}},
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            routing = OpenRouteServiceClient(api_key="test-secret", client=client)
            await routing.route(
                RouteCoordinate(latitude=24.86, longitude=67.01),
                RouteCoordinate(latitude=24.87, longitude=67.02),
                "car",
            )

    with pytest.raises(GeographicProviderError):
        asyncio.run(run())


def test_route_endpoint_returns_frontend_compatible_response() -> None:
    class StubRoutingClient:
        async def route(self, origin, destination, mode):
            return RouteResponse(
                geometry=RouteGeometry(
                    coordinates=[(67.01, 24.86), (67.02, 24.87)]
                ),
                distance_meters=1450.5,
                duration_seconds=420.25,
            )

    app.dependency_overrides[get_routing_client] = lambda: StubRoutingClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/routes/car",
                json={
                    "origin": {"latitude": 24.86, "longitude": 67.01},
                    "destination": {"latitude": 24.87, "longitude": 67.02},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "geometry": {
            "type": "LineString",
            "coordinates": [[67.01, 24.86], [67.02, 24.87]],
        },
        "distanceMeters": 1450.5,
        "durationSeconds": 420.25,
    }


def test_route_endpoint_surfaces_provider_rate_limit() -> None:
    class RateLimitedRoutingClient:
        async def route(self, origin, destination, mode):
            raise GeographicProviderError(
                "OpenRouteService",
                "Too many requests",
                status_code=429,
                retry_after="45",
            )

    app.dependency_overrides[get_routing_client] = (
        lambda: RateLimitedRoutingClient()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/routes/walk",
                json={
                    "origin": {"latitude": 24.86, "longitude": 67.01},
                    "destination": {"latitude": 24.87, "longitude": 67.02},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["retry-after"] == "45"
    assert response.json() == {"detail": "Routing provider rate limit reached"}


def test_route_endpoint_reports_missing_provider_configuration() -> None:
    class UnconfiguredRoutingClient:
        async def route(self, origin, destination, mode):
            raise RoutingConfigurationError("API key is not configured")

    app.dependency_overrides[get_routing_client] = (
        lambda: UnconfiguredRoutingClient()
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/routes/car",
                json={
                    "origin": {"latitude": 24.86, "longitude": 67.01},
                    "destination": {"latitude": 24.87, "longitude": 67.02},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Routing provider is not configured"}


def test_route_endpoint_validates_coordinates() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/routes/car",
            json={
                "origin": {"latitude": 91, "longitude": 67.01},
                "destination": {"latitude": 24.87, "longitude": 67.02},
            },
        )

    assert response.status_code == 422
