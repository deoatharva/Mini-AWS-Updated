import http.client
import json
import socket
import time
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
    raise RuntimeError("Could not find a free local port range for the compute tests.")


def _health_payload(port: int, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
        except OSError as exc:
            last_error = exc
        finally:
            connection.close()
        time.sleep(0.1)
    raise AssertionError(f"Worker health endpoint did not respond on port {port}: {last_error}")


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return _auth_headers(client, "compute-owner@example.com")


@pytest.fixture()
def compute_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    instances_dir = tmp_path / "instances"
    instances_dir.mkdir()
    port_start = _free_port_range()
    port_end = port_start + 5
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "compute_port_start", port_start)
    monkeypatch.setattr(settings, "compute_port_end", port_end)
    try:
        yield instances_dir
    finally:
        ProcessComputeAdapter(instances_dir, port_start, port_end).stop_all()


def _create_instance(
    client: TestClient, headers: dict[str, str], name: str = "Demo instance"
) -> dict:
    response = client.post(
        "/api/v1/compute/instances",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_get_and_validation(
    client: TestClient, compute_env: Path, auth_headers: dict[str, str]
) -> None:
    created = _create_instance(client, auth_headers, "First instance")

    assert created["name"] == "First instance"
    assert created["adapter"] == "process"
    assert created["status"] == "stopped"
    assert created["port"] is None
    assert created["pid"] is None
    assert created["local_url"] is None
    assert created["last_error"] is None
    assert created["created_at"].endswith(("Z", "+00:00"))

    listed = client.get("/api/v1/compute/instances", headers=auth_headers)
    assert listed.status_code == 200
    assert [instance["id"] for instance in listed.json()] == [created["id"]]

    fetched = client.get(
        f"/api/v1/compute/instances/{created['id']}", headers=auth_headers
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]

    blank = client.post(
        "/api/v1/compute/instances", json={"name": "   "}, headers=auth_headers
    )
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"
    assert any(detail["field"] == "name" for detail in blank.json()["error"]["details"])

    missing = client.get("/api/v1/compute/instances/999999", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "instance_not_found"


def test_compute_requires_authentication(client: TestClient, compute_env: Path) -> None:
    response = client.get("/api/v1/compute/instances")
    create = client.post("/api/v1/compute/instances", json={"name": "No auth"})

    assert response.status_code == 401
    assert create.status_code == 401


def test_ownership_is_enforced_for_every_instance_route(
    client: TestClient, compute_env: Path
) -> None:
    owner_headers = _auth_headers(client, "owner@example.com")
    other_headers = _auth_headers(client, "other@example.com")
    instance = _create_instance(client, owner_headers, "Owner only")
    instance_id = instance["id"]

    other_list = client.get("/api/v1/compute/instances", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json() == []

    for method, suffix in (
        ("get", ""),
        ("post", "/start"),
        ("post", "/stop"),
        ("delete", ""),
    ):
        response = client.request(
            method.upper(),
            f"/api/v1/compute/instances/{instance_id}{suffix}",
            headers=other_headers,
        )
        assert response.status_code == 403, (method, suffix, response.text)
        assert response.json()["error"]["code"] == "resource_forbidden"

    still_there = client.get(
        f"/api/v1/compute/instances/{instance_id}", headers=owner_headers
    )
    assert still_there.status_code == 200
    assert still_there.json()["status"] == "stopped"


def test_real_process_lifecycle_logs_and_delete(
    client: TestClient, compute_env: Path, auth_headers: dict[str, str]
) -> None:
    instance = _create_instance(client, auth_headers, "Worker lifecycle")
    instance_id = instance["id"]
    instance_dir = compute_env / str(instance_id)

    started = client.post(
        f"/api/v1/compute/instances/{instance_id}/start", headers=auth_headers
    )
    assert started.status_code == 200, started.text
    running = started.json()
    assert running["status"] == "running"
    assert running["pid"] and running["pid"] > 0
    assert running["port"] and settings.compute_port_start <= running["port"] <= settings.compute_port_end
    assert running["local_url"] == f"http://127.0.0.1:{running['port']}/"
    assert running["started_at"]
    assert _port_is_open(running["port"])

    health = _health_payload(running["port"])
    assert health["status"] == "ok"
    assert health["instance_id"] == instance_id
    assert health["pid"] == running["pid"]
    assert health["local_process_not_vm"] is True

    logs = client.get(
        f"/api/v1/compute/instances/{instance_id}/logs", headers=auth_headers
    )
    assert logs.status_code == 200
    assert "listening" in logs.json()["content"]
    assert logs.json()["truncated"] is False

    listed = client.get("/api/v1/compute/instances", headers=auth_headers)
    assert listed.json()[0]["status"] == "running"

    stopped = client.post(
        f"/api/v1/compute/instances/{instance_id}/stop", headers=auth_headers
    )
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["local_url"] is None
    assert _port_is_open(running["port"]) is False

    stopped_logs = client.get(
        f"/api/v1/compute/instances/{instance_id}/logs", headers=auth_headers
    )
    assert "stopped" in stopped_logs.json()["content"]

    restarted = client.post(
        f"/api/v1/compute/instances/{instance_id}/start", headers=auth_headers
    )
    assert restarted.status_code == 200, restarted.text
    assert restarted.json()["status"] == "running"
    new_port = restarted.json()["port"]
    assert _port_is_open(new_port)

    deleted = client.delete(
        f"/api/v1/compute/instances/{instance_id}", headers=auth_headers
    )
    assert deleted.status_code == 204
    assert not instance_dir.exists()
    assert _port_is_open(new_port) is False

    gone = client.get(
        f"/api/v1/compute/instances/{instance_id}", headers=auth_headers
    )
    assert gone.status_code == 404


def test_start_failure_is_persisted_honestly(
    client: TestClient,
    compute_env: Path,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        occupied_port = occupied.getsockname()[1]

        monkeypatch.setattr(settings, "compute_port_start", occupied_port)
        monkeypatch.setattr(settings, "compute_port_end", occupied_port)

        instance = _create_instance(client, auth_headers, "Cannot bind")
        response = client.post(
            f"/api/v1/compute/instances/{instance['id']}/start",
            headers=auth_headers,
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "instance_start_failed"

    fetched = client.get(
        f"/api/v1/compute/instances/{instance['id']}", headers=auth_headers
    )
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["status"] == "error"
    assert "No free local port" in body["last_error"]
    assert body["local_url"] is None
