from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from geoalchemy2.shape import to_shape
from pydantic import SecretStr

from app.api import admin
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.parking_spot import ParkingSpot


class FakeResult:
    def __init__(self, values: list[ParkingSpot]) -> None:
        self.values = values

    def all(self) -> list[ParkingSpot]:
        return self.values


class FakeSession:
    def __init__(self) -> None:
        self.spots: dict[UUID, ParkingSpot] = {}
        self.commits = 0

    def scalars(self, _statement: object) -> FakeResult:
        return FakeResult(list(self.spots.values()))

    def get(self, _model: type[ParkingSpot], key: UUID) -> ParkingSpot | None:
        return self.spots.get(key)

    def add(self, spot: ParkingSpot) -> None:
        spot.id = uuid4()
        spot.updated_at = datetime.now(timezone.utc)
        spot.created_at = spot.updated_at
        self.spots[spot.id] = spot

    def delete(self, spot: ParkingSpot) -> None:
        del self.spots[spot.id]

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _spot: ParkingSpot) -> None:
        return


def _client(session: FakeSession) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    return TestClient(app)


def test_admin_api_requires_a_configured_bearer_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_key", SecretStr("admin-secret"))
    session = FakeSession()
    try:
        with _client(session) as client:
            missing = client.get("/api/admin/parking")
            incorrect = client.get(
                "/api/admin/parking",
                headers={"Authorization": "Bearer wrong"},
            )
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 401
    assert incorrect.status_code == 401


def test_admin_api_is_disabled_when_no_key_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_key", None)
    session = FakeSession()
    try:
        with _client(session) as client:
            response = client.get(
                "/api/admin/parking",
                headers={"Authorization": "Bearer anything"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Parking administration is not configured"
    }


def test_admin_parking_crud_and_verification(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_key", SecretStr("admin-secret"))
    monkeypatch.setattr(admin, "to_shape", to_shape)
    session = FakeSession()
    try:
        with _client(session) as client:
            headers = {"Authorization": "Bearer admin-secret"}
            created = client.post(
                "/api/admin/parking",
                headers=headers,
                json={
                    "name": "Clifton visitor lot",
                    "address": "Clifton, Karachi",
                    "location": {"latitude": 24.81, "longitude": 67.03},
                    "parkingType": "parking",
                    "hourlyFee": 150,
                    "supportsCar": True,
                    "capacity": 40,
                },
            )
            spot_id = created.json()["id"]
            verified = client.patch(
                f"/api/admin/parking/{spot_id}",
                headers=headers,
                json={
                    "availabilityStatus": "verified",
                    "verificationStatus": "verified",
                },
            )
            verified_at = session.spots[UUID(spot_id)].last_verified_at
            unavailable = client.patch(
                f"/api/admin/parking/{spot_id}",
                headers=headers,
                json={"availabilityStatus": "unavailable"},
            )
            listed = client.get("/api/admin/parking", headers=headers)
            deleted = client.delete(
                f"/api/admin/parking/{spot_id}",
                headers=headers,
            )
            missing = client.get("/api/admin/parking", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["source"] == "admin"
    assert created.json()["location"] == {"latitude": 24.81, "longitude": 67.03}
    assert verified.status_code == 200
    assert verified.json()["verificationStatus"] == "verified"
    assert verified_at is not None
    assert unavailable.json()["availabilityStatus"] == "unavailable"
    assert len(listed.json()) == 1
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}
    assert missing.json() == []
    assert session.commits == 4


def test_admin_api_validates_records_and_reports_missing_ids(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_key", SecretStr("admin-secret"))
    session = FakeSession()
    try:
        with _client(session) as client:
            headers = {"Authorization": "Bearer admin-secret"}
            invalid = client.post(
                "/api/admin/parking",
                headers=headers,
                json={
                    "location": {"latitude": 100, "longitude": 67},
                    "hourlyFee": -1,
                },
            )
            missing = client.patch(
                f"/api/admin/parking/{uuid4()}",
                headers=headers,
                json={"name": "Missing"},
            )
    finally:
        app.dependency_overrides.clear()

    assert invalid.status_code == 422
    assert missing.status_code == 404
