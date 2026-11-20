from fastapi.testclient import TestClient

from app.api.destinations import get_geocoder
from app.main import app
from app.services.google_places import GooglePlace
from app.services.providers import GeographicProviderError


class StubPlaces:
    def __init__(self, results=(), error=None):
        self.results = results
        self.error = error
        self.calls = []

    async def search_destinations(self, query, limit=5, bias=None):
        self.calls.append((query, limit, bias))
        if self.error:
            raise self.error
        return self.results


def _get(query, provider, **params):
    app.dependency_overrides[get_geocoder] = lambda: provider
    try:
        with TestClient(app) as client:
            return client.get('/api/destinations/search', params={'q': query, **params})
    finally:
        app.dependency_overrides.clear()


def test_search_returns_google_place_without_persisting_it():
    provider = StubPlaces((GooglePlace(
        place_id='bahria-place', name='Bahria University Karachi',
        address='Karachi', latitude=24.893277, longitude=67.0881814,
        types=('university',),
    ),))
    response = _get('Bahria University Karachi', provider, limit=5,
                    latitude=24.8299, longitude=67.16)

    assert response.status_code == 200
    assert provider.calls == [('Bahria University Karachi', 5, (24.8299, 67.16))]
    assert response.json()['results'][0]['location'] == {
        'latitude': 24.893277, 'longitude': 67.0881814,
    }
    assert response.json()['results'][0]['name'] == 'Bahria University Karachi'


def test_search_reports_provider_rate_limit():
    response = _get('Saddar', StubPlaces(error=GeographicProviderError(
        'Google Places', 'Too many requests', status_code=429, retry_after='30',
    )))
    assert response.status_code == 429
    assert response.headers['retry-after'] == '30'


def test_search_reports_missing_key():
    response = _get('Saddar', StubPlaces(error=GeographicProviderError(
        'Google Places', 'API key is not configured', status_code=503,
    )))
    assert response.status_code == 503


def test_search_requires_paired_coordinates_and_non_whitespace_query():
    provider = StubPlaces()
    assert _get('Clifton', provider, latitude=24.8).status_code == 422
    assert _get('   ', provider).status_code == 422
    assert provider.calls == []
