from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings

PASSWORD = "correct-horse-battery-staple"


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": email.split("@")[0], "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def activity_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


def test_history_survives_resource_deletion(
    client: TestClient, activity_env: Path
) -> None:
    headers = _auth_headers(client, "history-owner@example.com")

    bucket = client.post(
        "/api/v1/storage/buckets",
        json={"name": "history-bucket"},
        headers=headers,
    ).json()
    uploaded = client.post(
        f"/api/v1/storage/buckets/{bucket['id']}/objects",
        files={"file": ("history.txt", b"history", "text/plain")},
        headers=headers,
    ).json()
    assert (
        client.delete(
            f"/api/v1/storage/buckets/{bucket['id']}/objects/{uploaded['id']}",
            headers=headers,
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/storage/buckets/{bucket['id']}", headers=headers
        ).status_code
        == 204
    )

    database = client.post(
        "/api/v1/databases", json={"name": "History DB"}, headers=headers
    ).json()
    assert (
        client.delete(
            f"/api/v1/databases/{database['id']}", headers=headers
        ).status_code
        == 204
    )

    deployment = client.post(
        "/api/v1/applications", json={"name": "History app"}, headers=headers
    ).json()
    assert (
        client.delete(
            f"/api/v1/applications/{deployment['id']}", headers=headers
        ).status_code
        == 204
    )

    instance = client.post(
        "/api/v1/compute/instances", json={"name": "History host"}, headers=headers
    ).json()
    assert (
        client.delete(
            f"/api/v1/compute/instances/{instance['id']}", headers=headers
        ).status_code
        == 204
    )

    response = client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()
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

    activity = body["recent_activity"]
    assert len(activity) == 10
    assert [(item["resource_type"], item["action"]) for item in activity] == [
        ("compute_instance", "deleted"),
        ("compute_instance", "created"),
        ("application", "deleted"),
        ("application", "deployed"),
        ("database", "deleted"),
        ("database", "created"),
        ("bucket", "deleted"),
        ("object", "deleted"),
        ("object", "uploaded"),
        ("bucket", "created"),
    ]
    assert activity[0]["resource_name"] == "History host"
    assert any(
        item["resource_name"] == "history-bucket/history.txt"
        for item in activity
    )


def test_history_is_limited_and_isolated_per_account(
    client: TestClient, activity_env: Path
) -> None:
    owner = _auth_headers(client, "activity-owner@example.com")
    other = _auth_headers(client, "activity-other@example.com")

    for number in range(1, 13):
        response = client.post(
            "/api/v1/compute/instances",
            json={"name": f"Instance {number}"},
            headers=owner,
        )
        assert response.status_code == 201

    activity = client.get("/api/v1/dashboard", headers=owner).json()[
        "recent_activity"
    ]
    assert len(activity) == 10
    assert activity[0]["resource_name"] == "Instance 12"
    assert activity[-1]["resource_name"] == "Instance 3"
    assert all(item["service"] == "compute" for item in activity)

    other_activity = client.get("/api/v1/dashboard", headers=other).json()[
        "recent_activity"
    ]
    assert other_activity == []
