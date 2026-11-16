import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.compute.process_adapter import ProcessComputeAdapter
from app.config import settings

PASSWORD = "correct-horse-battery-staple"


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": email.split("@")[0], "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _free_port_range() -> int:
    for _ in range(30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            start = probe.getsockname()[1]
        if start > 65000:
            continue
        try:
            for offset in range(6):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                    candidate.bind(("127.0.0.1", start + offset))
        except OSError:
            continue
        return start
    raise RuntimeError("Could not find a free local port range for dashboard tests.")


@pytest.fixture()
def dashboard_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    instances_dir = tmp_path / "instances"
    instances_dir.mkdir()
    compute_start = _free_port_range()
    compute_end = compute_start + 5
    application_start = compute_end + 1
    application_end = application_start + 5
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "compute_port_start", compute_start)
    monkeypatch.setattr(settings, "compute_port_end", compute_end)
    monkeypatch.setattr(settings, "application_port_start", application_start)
    monkeypatch.setattr(settings, "application_port_end", application_end)
    try:
        yield tmp_path
    finally:
        ProcessComputeAdapter(instances_dir, compute_start, compute_end).stop_all()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return _auth_headers(client, "dashboard-owner@example.com")


def test_empty_dashboard_and_authentication(
    client: TestClient, dashboard_env: Path
) -> None:
    assert client.get("/api/v1/dashboard").status_code == 401

    headers = _auth_headers(client, "empty-dashboard@example.com")
    response = client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["recent_activity"] == []
    assert body["counts"] == {
        "compute_total": 0,
        "compute_running": 0,
        "applications_total": 0,
        "applications_running": 0,
        "buckets_total": 0,
        "objects_total": 0,
        "storage_bytes": 0,
        "databases_total": 0,
    }


def test_dashboard_aggregates_real_resources_and_activity(
    client: TestClient, dashboard_env: Path, auth_headers: dict[str, str]
) -> None:
    assert (
        client.post(
            "/api/v1/compute/instances",
            json={"name": "Dashboard host"},
            headers=auth_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/applications",
            json={"name": "Dashboard app"},
            headers=auth_headers,
        ).status_code
        == 201
    )
    bucket = client.post(
        "/api/v1/storage/buckets",
        json={"name": "dashboard-bucket"},
        headers=auth_headers,
    )
    assert bucket.status_code == 201
    bucket_id = bucket.json()["id"]
    uploaded = client.post(
        f"/api/v1/storage/buckets/{bucket_id}/objects",
        files={"file": ("notes.txt", b"dashboard", "text/plain")},
        headers=auth_headers,
    )
    assert uploaded.status_code == 201
    assert (
        client.post(
            "/api/v1/databases",
            json={"name": "Dashboard DB"},
            headers=auth_headers,
        ).status_code
        == 201
    )

    response = client.get("/api/v1/dashboard", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    counts = body["counts"]
    assert counts["compute_total"] == 1
    assert counts["compute_running"] == 0
    assert counts["applications_total"] == 1
    assert counts["applications_running"] == 0
    assert counts["buckets_total"] == 1
    assert counts["objects_total"] == 1
    assert counts["storage_bytes"] == len(b"dashboard")
    assert counts["databases_total"] == 1

    activity = body["recent_activity"]
    assert len(activity) == 5
    assert {(item["resource_type"], item["action"]) for item in activity} == {
        ("compute_instance", "created"),
        ("application", "deployed"),
        ("bucket", "created"),
        ("object", "uploaded"),
        ("database", "created"),
    }
    assert all(item["timestamp"].endswith(("Z", "+00:00")) for item in activity)
    assert all(item["id"] and item["service"] for item in activity)


def test_dashboard_reflects_a_real_running_instance(
    client: TestClient, dashboard_env: Path, auth_headers: dict[str, str]
) -> None:
    instance = client.post(
        "/api/v1/compute/instances",
        json={"name": "Running for dashboard"},
        headers=auth_headers,
    )
    assert instance.status_code == 201
    instance_id = instance.json()["id"]

    started = client.post(
        f"/api/v1/compute/instances/{instance_id}/start", headers=auth_headers
    )
    assert started.status_code == 200, started.text
    port = started.json()["port"]

    try:
        response = client.get("/api/v1/dashboard", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["counts"]["compute_total"] == 1
        assert body["counts"]["compute_running"] == 1
        assert body["recent_activity"][0]["action"] == "started"
        assert body["recent_activity"][0]["resource_name"] == "Running for dashboard"
    finally:
        client.post(
            f"/api/v1/compute/instances/{instance_id}/stop", headers=auth_headers
        )

    stopped = client.get("/api/v1/dashboard", headers=auth_headers)
    assert stopped.json()["counts"]["compute_running"] == 0
    assert stopped.json()["recent_activity"][0]["action"] == "stopped"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        assert probe.connect_ex(("127.0.0.1", port)) != 0


def test_dashboard_is_isolated_per_account(
    client: TestClient, dashboard_env: Path
) -> None:
    owner = _auth_headers(client, "dashboard-owner@example.com")
    other = _auth_headers(client, "dashboard-other@example.com")

    client.post(
        "/api/v1/compute/instances",
        json={"name": "Owner instance"},
        headers=owner,
    )
    client.post(
        "/api/v1/storage/buckets",
        json={"name": "owner-bucket"},
        headers=owner,
    )
    client.post(
        "/api/v1/databases",
        json={"name": "Owner DB"},
        headers=owner,
    )

    own = client.get("/api/v1/dashboard", headers=owner).json()
    assert own["counts"]["compute_total"] == 1
    assert own["counts"]["buckets_total"] == 1
    assert own["counts"]["databases_total"] == 1
    assert own["recent_activity"]

    other_dashboard = client.get("/api/v1/dashboard", headers=other).json()
    assert other_dashboard["recent_activity"] == []
    assert other_dashboard["counts"]["compute_total"] == 0
    assert other_dashboard["counts"]["buckets_total"] == 0
    assert other_dashboard["counts"]["databases_total"] == 0
