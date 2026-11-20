import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.schemas.routing import RouteCoordinate
from app.services.google_routes import GoogleRoutesClient
from app.services.providers import GeographicProviderError
from app.services.routing import RoutingConfigurationError


@pytest.mark.parametrize(('mode', 'travel_mode'), [
    ('car', 'DRIVE'), ('bike', 'DRIVE'), ('walk', 'WALK'),
])
def test_google_routes_uses_geojson_and_normalizes_response(monkeypatch, mode, travel_mode):
    monkeypatch.setattr(settings, 'google_maps_api_key', SecretStr('test-key'))
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'routes': [{
            'distanceMeters': 1450,
            'duration': '420.5s',
            'polyline': {'geoJsonLinestring': {
                'type': 'LineString',
                'coordinates': [[67.01, 24.86], [67.02, 24.87]],
            }},
        }]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await GoogleRoutesClient(client).route(
                RouteCoordinate(latitude=24.86, longitude=67.01),
                RouteCoordinate(latitude=24.87, longitude=67.02), mode,
            )

    result = asyncio.run(run())
    assert requests[0].headers['X-Goog-FieldMask'].endswith('geoJsonLinestring')
    assert json.loads(requests[0].content)['travelMode'] == travel_mode
    assert result.geometry.coordinates == [(67.01, 24.86), (67.02, 24.87)]
    assert result.distance_meters == 1450
    assert result.duration_seconds == 420.5


def test_google_routes_requires_key(monkeypatch):
    monkeypatch.setattr(settings, 'google_maps_api_key', None)
    with pytest.raises(RoutingConfigurationError):
        asyncio.run(GoogleRoutesClient().route(
            RouteCoordinate(latitude=24.86, longitude=67.01),
            RouteCoordinate(latitude=24.87, longitude=67.02), 'walk',
        ))


def test_google_routes_rejects_invalid_geometry(monkeypatch):
    monkeypatch.setattr(settings, 'google_maps_api_key', SecretStr('test-key'))

    def handler(request):
        return httpx.Response(200, json={'routes': [{
            'distanceMeters': 1, 'duration': '1s',
            'polyline': {'geoJsonLinestring': {'type': 'Point', 'coordinates': [67, 24]}},
        }]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await GoogleRoutesClient(client).route(
                RouteCoordinate(latitude=24.86, longitude=67.01),
                RouteCoordinate(latitude=24.87, longitude=67.02), 'walk',
            )

    with pytest.raises(GeographicProviderError):
        asyncio.run(run())
