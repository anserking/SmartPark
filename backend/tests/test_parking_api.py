from fastapi.testclient import TestClient

from app.api.parking import get_overpass_client
from app.main import app
from app.services.parking_normalization import NormalizedParking
from app.services.providers import GeographicProviderError


class StubOverpass:
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
    )


def test_search_returns_nearest_openstreetmap_parking_facilities() -> None:
    provider = StubOverpass(
        facilities=(
            _facility("way/near", 67.021, 24.855, "Near lot"),
            _facility("node/far", 67.04, 24.87, "Far lot"),
        )
    )
    app.dependency_overrides[get_overpass_client] = lambda: provider
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
    assert results[0]["source"] == "openstreetmap"
    assert results[0]["verificationStatus"] == "unverified"
    assert results[0]["availabilityStatus"] == "unknown"


def test_search_surfaces_overpass_rate_limits() -> None:
    provider = StubOverpass(
        error=GeographicProviderError(
            "Overpass",
            "Too many requests",
            status_code=429,
            retry_after="30",
        )
    )
    app.dependency_overrides[get_overpass_client] = lambda: provider
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
        "detail": "OpenStreetMap parking search rate limit reached"
    }
