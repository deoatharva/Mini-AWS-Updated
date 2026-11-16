import http.client
import json
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.deployment.local_app_runner import LocalAppRunner
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
    raise RuntimeError("Could not find a free local port range for the application tests.")


def _get(port: int, path: str) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2.0)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture()
def application_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    applications_dir = tmp_path / "applications"
    applications_dir.mkdir()
    port_start = _free_port_range()
    port_end = port_start + 5
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "application_port_start", port_start)
    monkeypatch.setattr(settings, "application_port_end", port_end)
    try:
        yield applications_dir
    finally:
        LocalAppRunner(applications_dir, port_start, port_end).stop_all()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return _auth_headers(client, "app-owner@example.com")


def _create_deployment(
    client: TestClient, headers: dict[str, str], name: str = "Sample app"
) -> dict:
    response = client.post(
        "/api/v1/applications",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_get_and_validation(
    client: TestClient, application_env: Path, auth_headers: dict[str, str]
) -> None:
    created = _create_deployment(client, auth_headers, "Practical app")

    assert created["name"] == "Practical app"
    assert created["template"] == "sample-web-app"
    assert created["status"] == "stopped"
    assert created["local_url"] is None
    assert created["pid"] is None
    assert created["created_at"].endswith(("Z", "+00:00"))

    listed = client.get("/api/v1/applications", headers=auth_headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]

    fetched = client.get(f"/api/v1/applications/{created['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["template"] == "sample-web-app"

    blank = client.post("/api/v1/applications", json={"name": "   "}, headers=auth_headers)
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"

    missing = client.get("/api/v1/applications/999999", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "application_not_found"


def test_application_requires_authentication(
    client: TestClient, application_env: Path
) -> None:
    listed = client.get("/api/v1/applications")
    created = client.post("/api/v1/applications", json={"name": "No auth"})
    assert listed.status_code == 401
    assert created.status_code == 401


def test_application_ownership(
    client: TestClient, application_env: Path
) -> None:
    owner = _auth_headers(client, "app-owner@example.com")
    other = _auth_headers(client, "app-other@example.com")
    deployment = _create_deployment(client, owner, "Owner app")
    deployment_id = deployment["id"]

    other_list = client.get("/api/v1/applications", headers=other)
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
            f"/api/v1/applications/{deployment_id}{suffix}",
            headers=other,
        )
        assert response.status_code == 403, (method, suffix, response.text)
        assert response.json()["error"]["code"] == "resource_forbidden"

    still_there = client.get(
        f"/api/v1/applications/{deployment_id}", headers=owner
    )
    assert still_there.json()["status"] == "stopped"


def test_real_sample_app_lifecycle_and_delete(
    client: TestClient, application_env: Path, auth_headers: dict[str, str]
) -> None:
    deployment = _create_deployment(client, auth_headers, "Controlled sample")
    deployment_id = deployment["id"]
    deployment_dir = application_env / str(deployment_id)

    started = client.post(
        f"/api/v1/applications/{deployment_id}/start", headers=auth_headers
    )
    assert started.status_code == 200, started.text
    running = started.json()
    assert running["status"] == "running"
    assert running["pid"] and running["pid"] > 0
    assert settings.application_port_start <= running["port"] <= settings.application_port_end
    assert running["local_url"] == f"http://127.0.0.1:{running['port']}/"
    assert _port_is_open(running["port"])

    health_status, _, health_body = _get(running["port"], "/health")
    health = json.loads(health_body)
    assert health_status == 200
    assert health["status"] == "ok"
    assert health["instance_id"] == deployment_id
    assert health["template"] == "sample-web-app"

    page_status, _, page_body = _get(running["port"], "/")
    page = page_body.decode("utf-8")
    assert page_status == 200
    assert "Controlled sample" in page
    assert "CONTROLLED SAMPLE WEB APPLICATION" in page

    info_status, _, info_body = _get(running["port"], "/api/info")
    info = json.loads(info_body)
    assert info_status == 200
    assert info["deployment_id"] == deployment_id
    assert info["name"] == "Controlled sample"
    assert info["template"] == "sample-web-app"

    logs = client.get(
        f"/api/v1/applications/{deployment_id}/logs", headers=auth_headers
    )
    assert logs.status_code == 200
    assert "[app] deployment" in logs.json()["content"]
    assert "listening" in logs.json()["content"]

    listed = client.get("/api/v1/applications", headers=auth_headers)
    assert listed.json()[0]["status"] == "running"

    stopped = client.post(
        f"/api/v1/applications/{deployment_id}/stop", headers=auth_headers
    )
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["local_url"] is None
    assert _port_is_open(running["port"]) is False

    restarted = client.post(
        f"/api/v1/applications/{deployment_id}/start", headers=auth_headers
    )
    assert restarted.status_code == 200, restarted.text
    assert restarted.json()["status"] == "running"
    second_port = restarted.json()["port"]
    assert _port_is_open(second_port)

    deleted = client.delete(
        f"/api/v1/applications/{deployment_id}", headers=auth_headers
    )
    assert deleted.status_code == 204
    assert not deployment_dir.exists()
    assert _port_is_open(second_port) is False

    gone = client.get(f"/api/v1/applications/{deployment_id}", headers=auth_headers)
    assert gone.status_code == 404


def test_application_start_failure_is_persisted(
    client: TestClient,
    application_env: Path,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        occupied_port = occupied.getsockname()[1]
        monkeypatch.setattr(settings, "application_port_start", occupied_port)
        monkeypatch.setattr(settings, "application_port_end", occupied_port)

        deployment = _create_deployment(client, auth_headers, "Port failure")
        response = client.post(
            f"/api/v1/applications/{deployment['id']}/start",
            headers=auth_headers,
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "application_start_failed"

    fetched = client.get(
        f"/api/v1/applications/{deployment['id']}", headers=auth_headers
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "error"
    assert "No free local port" in fetched.json()["last_error"]
    assert fetched.json()["local_url"] is None
