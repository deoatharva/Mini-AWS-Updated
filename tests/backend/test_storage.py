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
def storage_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "max_upload_bytes", 1024 * 1024)
    return tmp_path


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return _auth_headers(client, "storage-owner@example.com")


def _create_bucket(
    client: TestClient, headers: dict[str, str], name: str = "practical-bucket"
) -> dict:
    response = client.post(
        "/api/v1/storage/buckets",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload(
    client: TestClient,
    headers: dict[str, str],
    bucket_id: int,
    filename: str = "notes.txt",
    content: bytes = b"local object storage",
    content_type: str = "text/plain",
):
    return client.post(
        f"/api/v1/storage/buckets/{bucket_id}/objects",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def _stored_files(root: Path) -> list[Path]:
    return list((root / "buckets").rglob("*.bin"))


def test_create_validation_list_and_duplicate(
    client: TestClient, storage_env: Path, auth_headers: dict[str, str]
) -> None:
    created = _create_bucket(client, auth_headers, "Practical-Bucket")

    assert created["name"] == "practical-bucket"
    assert created["object_count"] == 0
    assert created["total_bytes"] == 0
    assert created["created_at"].endswith(("Z", "+00:00"))

    listed = client.get("/api/v1/storage/buckets", headers=auth_headers)
    assert listed.status_code == 200
    assert [bucket["id"] for bucket in listed.json()] == [created["id"]]

    duplicate = client.post(
        "/api/v1/storage/buckets",
        json={"name": "PRACTICAL-BUCKET"},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "bucket_already_exists"

    for invalid_name in (
        "ab",
        "bad_name",
        "-leading",
        "trailing-",
        "double..dot",
        "has space",
    ):
        response = client.post(
            "/api/v1/storage/buckets",
            json={"name": invalid_name},
            headers=auth_headers,
        )
        assert response.status_code == 422, invalid_name
        assert response.json()["error"]["code"] == "validation_error"

    missing = client.get("/api/v1/storage/buckets/999999/objects", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "bucket_not_found"


def test_storage_requires_authentication(
    client: TestClient, storage_env: Path
) -> None:
    assert client.get("/api/v1/storage/buckets").status_code == 401
    assert (
        client.post(
            "/api/v1/storage/buckets", json={"name": "no-auth-bucket"}
        ).status_code
        == 401
    )


def test_storage_ownership(
    client: TestClient, storage_env: Path
) -> None:
    owner = _auth_headers(client, "storage-owner@example.com")
    other = _auth_headers(client, "storage-other@example.com")
    bucket = _create_bucket(client, owner)
    uploaded = _upload(client, owner, bucket["id"])
    assert uploaded.status_code == 201
    object_id = uploaded.json()["id"]

    assert client.get("/api/v1/storage/buckets", headers=other).json() == []

    requests = (
        ("get", f"/api/v1/storage/buckets/{bucket['id']}/objects", None),
        (
            "delete",
            f"/api/v1/storage/buckets/{bucket['id']}",
            None,
        ),
        (
            "delete",
            f"/api/v1/storage/buckets/{bucket['id']}/objects/{object_id}",
            None,
        ),
        (
            "get",
            f"/api/v1/storage/buckets/{bucket['id']}/objects/{object_id}/download",
            None,
        ),
    )
    for method, path, body in requests:
        response = client.request(method.upper(), path, headers=other, json=body)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["error"]["code"] == "resource_forbidden"

    denied_upload = _upload(client, other, bucket["id"], "denied.txt", b"nope")
    assert denied_upload.status_code == 403
    assert denied_upload.json()["error"]["code"] == "resource_forbidden"

    same_name_other_account = _create_bucket(client, other)
    assert same_name_other_account["name"] == "practical-bucket"


def test_upload_list_download_overwrite_and_delete(
    client: TestClient, storage_env: Path, auth_headers: dict[str, str]
) -> None:
    bucket = _create_bucket(client, auth_headers)
    bucket_id = bucket["id"]

    uploaded = _upload(client, auth_headers, bucket_id, "notes.txt", b"hello storage")
    assert uploaded.status_code == 201, uploaded.text
    first = uploaded.json()
    assert first["object_key"] == "notes.txt"
    assert first["size_bytes"] == len(b"hello storage")
    assert first["content_type"] == "text/plain"
    assert len(first["etag"]) == 64
    assert len(_stored_files(storage_env)) == 1

    listed = client.get(
        f"/api/v1/storage/buckets/{bucket_id}/objects", headers=auth_headers
    )
    assert listed.status_code == 200
    assert [item["object_key"] for item in listed.json()] == ["notes.txt"]

    buckets = client.get("/api/v1/storage/buckets", headers=auth_headers)
    summary = buckets.json()[0]
    assert summary["object_count"] == 1
    assert summary["total_bytes"] == len(b"hello storage")

    download = client.get(
        f"/api/v1/storage/buckets/{bucket_id}/objects/{first['id']}/download",
        headers=auth_headers,
    )
    assert download.status_code == 200
    assert download.content == b"hello storage"
    assert "notes.txt" in download.headers["content-disposition"]
    assert download.headers["etag"] == f'"{first["etag"]}"'

    overwritten = _upload(
        client, auth_headers, bucket_id, "notes.txt", b"new content", "text/markdown"
    )
    assert overwritten.status_code == 201, overwritten.text
    assert overwritten.json()["id"] == first["id"]
    assert overwritten.json()["size_bytes"] == len(b"new content")
    assert overwritten.json()["content_type"] == "text/markdown"
    assert overwritten.json()["etag"] != first["etag"]
    assert len(_stored_files(storage_env)) == 1

    download_new = client.get(
        f"/api/v1/storage/buckets/{bucket_id}/objects/{first['id']}/download",
        headers=auth_headers,
    )
    assert download_new.content == b"new content"

    non_empty_delete = client.delete(
        f"/api/v1/storage/buckets/{bucket_id}", headers=auth_headers
    )
    assert non_empty_delete.status_code == 409
    assert non_empty_delete.json()["error"]["code"] == "bucket_not_empty"

    deleted = client.delete(
        f"/api/v1/storage/buckets/{bucket_id}/objects/{first['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204
    assert _stored_files(storage_env) == []

    missing_download = client.get(
        f"/api/v1/storage/buckets/{bucket_id}/objects/{first['id']}/download",
        headers=auth_headers,
    )
    assert missing_download.status_code == 404
    assert missing_download.json()["error"]["code"] == "object_not_found"

    deleted_bucket = client.delete(
        f"/api/v1/storage/buckets/{bucket_id}", headers=auth_headers
    )
    assert deleted_bucket.status_code == 204
    assert not (storage_env / "buckets" / "1" / str(bucket_id)).exists()
    assert client.get("/api/v1/storage/buckets", headers=auth_headers).json() == []


def test_upload_rejects_unsafe_names_and_oversized_files(
    client: TestClient,
    storage_env: Path,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bucket = _create_bucket(client, auth_headers)
    bucket_id = bucket["id"]

    for unsafe_name in ("../escape.txt", "folder/file.txt", "CON.txt", ".hidden"):
        response = _upload(client, auth_headers, bucket_id, unsafe_name, b"nope")
        assert response.status_code == 422, unsafe_name
        assert response.json()["error"]["code"] == "invalid_object_key"
    assert _stored_files(storage_env) == []

    monkeypatch.setattr(settings, "max_upload_bytes", 4)
    too_large = _upload(client, auth_headers, bucket_id, "large.txt", b"12345")
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "file_too_large"
    assert _stored_files(storage_env) == []

    listed = client.get(
        f"/api/v1/storage/buckets/{bucket_id}/objects", headers=auth_headers
    )
    assert listed.json() == []
    summary = client.get("/api/v1/storage/buckets", headers=auth_headers).json()[0]
    assert summary["object_count"] == 0
    assert summary["total_bytes"] == 0
