from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db
from app.main import app


def test_health_endpoint_reports_connected_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mini-aws-api",
        "version": "0.1.0",
        "mode": "local",
        "database": "connected",
    }


class _UnavailableSession:
    def execute(self, *args, **kwargs):
        raise SQLAlchemyError("database unavailable")


def test_health_endpoint_reports_degraded_database(client: TestClient) -> None:
    def override_get_db() -> Iterator[_UnavailableSession]:
        yield _UnavailableSession()

    app.dependency_overrides[get_db] = override_get_db
    response = client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


def test_unknown_api_route_uses_consistent_error_payload(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not Found"}
    }
