from fastapi.testclient import TestClient

from app.api.parking import get_google_places_client
from app.db.session import get_db
from app.main import app
from app.services.parking_normalization import NormalizedParking
from app.services.providers import GeographicProviderError


class StubPlaces:
    def __init__(
        self,
        facilities: tuple[NormalizedParking, ...] = (),
        error: GeographicProviderError | None = None,
    ) -> None:
        self.facilities = facilities
        self.error = error
        self.request: tuple[float, float, int] | None = None

    async def nearby_parking(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int,
    ) -> tuple[NormalizedParking, ...]:
        self.request = (latitude, longitude, radius_meters)
        if self.error is not None:
            raise self.error
        return self.facilities


def _facility(
    osm_id: str,
    longitude: float,
    latitude: float,
    name: str | None = None,
) -> NormalizedParking:
    return NormalizedParking(
        osm_id=osm_id,
        name=name,
        geometry={"type": "Point", "coordinates": [longitude, latitude]},
        parking_type="parking",
        fee="yes",
        capacity=30,
        access=None,
        supports_car=True,
        supports_bike=None,
        tags={"addr:street": "Main Road", "addr:city": "Karachi"},
        source="google_maps",
    )


def test_search_returns_nearest_google_parking_facilities() -> None:
    provider = StubPlaces(
        facilities=(
            _facility("way/near", 67.021, 24.855, "Near lot"),
            _facility("node/far", 67.04, 24.87, "Far lot"),
        )
    )
    app.dependency_overrides[get_google_places_client] = lambda: provider
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/parking/search",
                params={
                    "latitude": 24.8546842,
                    "longitude": 67.0207055,
                    "radius_meters": 1200,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert provider.request == (24.8546842, 67.0207055, 1200)
    results = response.json()["results"]
    assert [facility["id"] for facility in results] == ["way/near", "node/far"]
    assert results[0]["location"] == {"latitude": 24.855, "longitude": 67.021}
    assert results[0]["address"] == "Main Road, Karachi"
    assert results[0]["straightLineDistanceMeters"] > 0
    assert results[0]["source"] == "google_maps"
    assert results[0]["verificationStatus"] == "unverified"
    assert results[0]["availabilityStatus"] == "unknown"


def test_search_surfaces_google_rate_limits() -> None:
    provider = StubPlaces(
        error=GeographicProviderError(
            "Google Places",
            "Too many requests",
            status_code=429,
            retry_after="30",
        )
    )
    app.dependency_overrides[get_google_places_client] = lambda: provider
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/parking/search",
                params={"latitude": 24.86, "longitude": 67.03},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    assert response.json() == {
        "detail": "Google parking search rate limit reached"
    }


def test_recommendations_filter_vehicle_compatibility_and_label_fallback() -> None:
    class EmptySession:
        def scalars(self, _statement: object):
            class Result:
                def all(self) -> list[object]:
                    return []

            return Result()

    provider = StubPlaces(
        facilities=(
            _facility("node/car", 67.021, 24.855, "Car parking"),
            NormalizedParking(
                osm_id="node/bike",
                name="Bike parking",
                geometry={"type": "Point", "coordinates": [67.022, 24.855]},
                parking_type="motorcycle_parking",
                fee=None,
                capacity=None,
                access=None,
                supports_car=False,
                supports_bike=True,
                tags={},
            ),
        )
    )
    app.dependency_overrides[get_google_places_client] = lambda: provider
    app.dependency_overrides[get_db] = lambda: (yield EmptySession())
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/parking/recommendations",
                params={
                    "latitude": 24.8546842,
                    "longitude": 67.0207055,
                    "vehicle_type": "car",
                    "user_latitude": 24.86,
                    "user_longitude": 67.03,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["distanceMethod"] == "straight_line"
    assert [spot["id"] for spot in payload["results"]] == ["node/car"]
    assert payload["results"][0]["destinationDistanceMethod"] == "straight_line"
    assert payload["results"][0]["userDistanceMeters"] > 0
