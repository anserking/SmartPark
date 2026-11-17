import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/smartpark_test",
)

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


class HealthSession:
    def execute(self, statement: object) -> None:
        return None


def override_get_db():
    yield HealthSession()


def test_health_reports_database_connection() -> None:
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_reports_database_failure() -> None:
    class BrokenHealthSession:
        def execute(self, statement: object) -> None:
            raise OperationalError("SELECT 1", {}, RuntimeError("database offline"))

    def override_broken_db():
        yield BrokenHealthSession()

    app.dependency_overrides[get_db] = override_broken_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
