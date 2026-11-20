import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.services.google_places import GooglePlacesClient
from app.services.providers import GeographicProviderError


def test_google_text_and_nearby_parking_requests(monkeypatch):
    monkeypatch.setattr(settings, 'google_maps_api_key', SecretStr('test-key'))
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'places': [{
            'id': 'place-123', 'displayName': {'text': 'Bahria University Karachi'},
            'formattedAddress': 'Karachi, Pakistan',
            'location': {'latitude': 24.893277, 'longitude': 67.0881814},
            'types': ['parking'],
        }]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = GooglePlacesClient(client)
            return (await provider.search_destinations('Bahria University Karachi'),
                    await provider.nearby_parking(24.893277, 67.0881814))

    destinations, parking = asyncio.run(run())
    assert destinations[0].name == 'Bahria University Karachi'
    assert parking[0].source == 'google_maps'
    assert parking[0].geometry['coordinates'] == [67.0881814, 24.893277]
    assert requests[0].url.path.endswith(':searchText')
    assert requests[1].url.path.endswith(':searchNearby')
    assert json.loads(requests[1].content)['includedTypes'] == ['parking']
    assert json.loads(requests[1].content)['rankPreference'] == 'DISTANCE'
    assert requests[0].headers['X-Goog-FieldMask'].startswith('places.id')


def test_google_provider_requires_key(monkeypatch):
    monkeypatch.setattr(settings, 'google_maps_api_key', None)
    with pytest.raises(GeographicProviderError) as error:
        asyncio.run(GooglePlacesClient().search_destinations('Bahria University Karachi'))
    assert error.value.status_code == 503


def test_destination_text_search_recovers_misclassified_car_park(monkeypatch):
    monkeypatch.setattr(settings, 'google_maps_api_key', SecretStr('test-key'))
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith(':searchNearby'):
            return httpx.Response(200, json={'places': []})
        return httpx.Response(200, json={'places': [{
            'id': 'bahria-car-park',
            'displayName': {'text': 'Bahria University Car Park'},
            'formattedAddress': 'National Stadium Road, Karachi',
            'location': {'latitude': 24.8931744, 'longitude': 67.086021},
            'types': ['premise', 'street_address'],
        }, {
            'id': 'not-parking',
            'displayName': {'text': 'Bahria Auditorium'},
            'location': {'latitude': 24.8932, 'longitude': 67.0861},
            'types': ['premise'],
        }]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await GooglePlacesClient(client).nearby_parking(
                24.893277, 67.0881814, radius_meters=300,
                destination_name='Bahria University Karachi',
            )

    results = asyncio.run(run())
    assert [place.name for place in results] == ['Bahria University Car Park']
    assert len(requests) == 2
    assert json.loads(requests[1].content)['textQuery'] == 'parking near Bahria University Karachi'
