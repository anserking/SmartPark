from uuid import UUID

from fastapi.testclient import TestClient

from app.api.destinations import (
    DestinationSearchIndex,
    get_geocoder,
    get_search_index,
)
from app.db.session import get_db
from app.main import app
from app.models.destination import Destination
from app.services.geocoding import DestinationCandidate
from app.services.providers import GeographicProviderError


class FakeSession:
    def __init__(self) -> None:
        self.destinations: dict[UUID, Destination] = {}
        self.commits = 0

    def get(self, model: type[Destination], key: UUID) -> Destination | None:
        return self.destinations.get(key)

    def add(self, destination: Destination) -> None:
        self.destinations[destination.id] = destination

    def commit(self) -> None:
        self.commits += 1


class StubGeocoder:
    def __init__(self, results: dict[str, tuple[DestinationCandidate, ...]]) -> None:
        self.results = results

    async def search(
        self,
        query: str,
        limit: int,
        bias: tuple[float, float] | None,
    ) -> tuple[DestinationCandidate, ...]:
        return self.results.get(query, ())


def test_search_persists_results_and_uses_trie_for_cached_prefixes() -> None:
    candidate = DestinationCandidate(
        name="Bahria University Karachi",
        category="college",
        address="Karachi",
        latitude=24.86,
        longitude=67.03,
        osm_id="W/456",
    )
    session = FakeSession()
    search_index = DestinationSearchIndex()
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_geocoder] = lambda: StubGeocoder(
        {"Bahria University": (candidate,), "Bahria": ()}
    )
    app.dependency_overrides[get_search_index] = lambda: search_index
    try:
        with TestClient(app) as client:
            first = client.get(
                "/api/destinations/search",
                params={"q": "Bahria University"},
            )
            second = client.get(
                "/api/destinations/search",
                params={"q": "Bahria"},
            )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["results"][0]["id"] == second.json()["results"][0]["id"]
    assert first.json()["results"][0]["location"] == {
        "latitude": 24.86,
        "longitude": 67.03,
    }
    assert len(session.destinations) == 1
    assert session.commits == 2


def test_search_reports_provider_rate_limit() -> None:
    class RateLimitedGeocoder:
        async def search(
            self,
            query: str,
            limit: int,
            bias: tuple[float, float] | None,
        ) -> tuple[DestinationCandidate, ...]:
            raise GeographicProviderError(
                "Photon",
                "Too many requests",
                status_code=429,
                retry_after="30",
            )

    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_geocoder] = lambda: RateLimitedGeocoder()
    app.dependency_overrides[get_search_index] = lambda: DestinationSearchIndex()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/destinations/search",
                params={"q": "Saddar"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    assert response.json() == {"detail": "Destination provider rate limit reached"}


def test_search_reports_unavailable_provider() -> None:
    class UnavailableGeocoder:
        async def search(
            self,
            query: str,
            limit: int,
            bias: tuple[float, float] | None,
        ) -> tuple[DestinationCandidate, ...]:
            raise GeographicProviderError("Photon", "Provider timeout")

    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_geocoder] = lambda: UnavailableGeocoder()
    app.dependency_overrides[get_search_index] = lambda: DestinationSearchIndex()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/destinations/search",
                params={"q": "Saddar"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Destination search provider is unavailable"}


def test_search_requires_paired_coordinates_and_non_whitespace_query() -> None:
    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_geocoder] = lambda: StubGeocoder({})
    app.dependency_overrides[get_search_index] = lambda: DestinationSearchIndex()
    try:
        with TestClient(app) as client:
            partial_location = client.get(
                "/api/destinations/search",
                params={"q": "Clifton", "latitude": 24.8},
            )
            whitespace_query = client.get(
                "/api/destinations/search",
                params={"q": "   "},
            )
    finally:
        app.dependency_overrides.clear()

    assert partial_location.status_code == 422
    assert partial_location.json() == {
        "detail": "Latitude and longitude must be provided together"
    }
    assert whitespace_query.status_code == 422
    assert whitespace_query.json() == {
        "detail": "Search query must contain at least two characters"
    }
