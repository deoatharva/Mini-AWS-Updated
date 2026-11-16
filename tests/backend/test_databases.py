from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.databases.sqlite_adapter import MAX_RESULT_ROWS
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
def database_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return _auth_headers(client, "database-owner@example.com")


def _create_database(
    client: TestClient, headers: dict[str, str], name: str = "Practical DB"
) -> dict:
    response = client.post(
        "/api/v1/databases",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _query(
    client: TestClient, headers: dict[str, str], database_id: int, sql: str
):
    return client.post(
        f"/api/v1/databases/{database_id}/query",
        json={"sql": sql},
        headers=headers,
    )


def _database_file(root: Path, user_id: int, database_id: int) -> Path:
    return root / "databases" / str(user_id) / f"{database_id}.sqlite3"


def test_create_validation_list_and_duplicate(
    client: TestClient, database_env: Path, auth_headers: dict[str, str]
) -> None:
    created = _create_database(client, auth_headers, "Practical DB")

    assert created["name"] == "Practical DB"
    assert created["engine"] == "sqlite"
    assert created["status"] == "available"
    assert created["table_count"] == 0
    assert created["last_error"] is None
    assert created["created_at"].endswith(("Z", "+00:00"))
    assert _database_file(database_env, 1, created["id"]).is_file()

    listed = client.get("/api/v1/databases", headers=auth_headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]

    duplicate = client.post(
        "/api/v1/databases",
        json={"name": "PRACTICAL db"},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "database_already_exists"

    blank = client.post("/api/v1/databases", json={"name": "   "}, headers=auth_headers)
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"

    missing = client.get("/api/v1/databases/999999/tables", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "database_not_found"


def test_database_requires_authentication(
    client: TestClient, database_env: Path
) -> None:
    assert client.get("/api/v1/databases").status_code == 401
    assert (
        client.post("/api/v1/databases", json={"name": "No auth"}).status_code == 401
    )


def test_database_ownership(
    client: TestClient, database_env: Path
) -> None:
    owner = _auth_headers(client, "database-owner@example.com")
    other = _auth_headers(client, "database-other@example.com")
    database = _create_database(client, owner)
    database_id = database["id"]

    assert client.get("/api/v1/databases", headers=other).json() == []

    for method, suffix in (
        ("get", "/tables"),
        ("post", "/query"),
        ("delete", ""),
    ):
        body = {"sql": "SELECT 1"} if suffix == "/query" else None
        response = client.request(
            method.upper(),
            f"/api/v1/databases/{database_id}{suffix}",
            headers=other,
            json=body,
        )
        assert response.status_code == 403, (method, suffix, response.text)
        assert response.json()["error"]["code"] == "resource_forbidden"

    same_name_other_account = _create_database(client, other)
    assert same_name_other_account["name"] == "Practical DB"


def test_sql_create_insert_select_and_table_metadata(
    client: TestClient, database_env: Path, auth_headers: dict[str, str]
) -> None:
    database = _create_database(client, auth_headers)
    database_id = database["id"]

    created = _query(
        client,
        auth_headers,
        database_id,
        "CREATE TABLE notes ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT NOT NULL, "
        "body TEXT DEFAULT 'empty'"
        ")",
    )
    assert created.status_code == 200, created.text
    assert created.json()["statement_type"] == "CREATE"
    assert created.json()["columns"] == []
    assert created.json()["rows"] == []

    inserted = _query(
        client,
        auth_headers,
        database_id,
        "INSERT INTO notes (title, body) VALUES ('First note', 'Hello local SQLite')",
    )
    assert inserted.status_code == 200, inserted.text
    assert inserted.json()["rows_affected"] == 1

    selected = _query(
        client, auth_headers, database_id, "SELECT id, title, body FROM notes"
    )
    assert selected.status_code == 200, selected.text
    payload = selected.json()
    assert payload["columns"] == ["id", "title", "body"]
    assert payload["rows"] == [[1, "First note", "Hello local SQLite"]]
    assert payload["truncated"] is False
    assert payload["duration_ms"] >= 0

    tables = client.get(
        f"/api/v1/databases/{database_id}/tables", headers=auth_headers
    )
    assert tables.status_code == 200, tables.text
    assert len(tables.json()) == 1
    table = tables.json()[0]
    assert table["name"] == "notes"
    assert table["kind"] == "table"
    columns = {column["name"]: column for column in table["columns"]}
    assert columns["id"]["primary_key"] is True
    assert columns["title"]["not_null"] is True
    assert columns["body"]["default_value"] == "'empty'"

    summary = client.get("/api/v1/databases", headers=auth_headers).json()[0]
    assert summary["table_count"] == 1
    assert summary["status"] == "available"


def test_sql_errors_are_honest_and_dangerous_statements_are_denied(
    client: TestClient, database_env: Path, auth_headers: dict[str, str]
) -> None:
    database = _create_database(client, auth_headers)
    database_id = database["id"]

    invalid = _query(client, auth_headers, database_id, "SELECT * FROM missing_table")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "sql_error"
    assert "no such table" in invalid.json()["error"]["message"]

    blank = _query(client, auth_headers, database_id, "   ")
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"

    for statement in (
        "ATTACH DATABASE 'other.sqlite3' AS other",
        "DETACH DATABASE other",
        "PRAGMA table_info('sqlite_master')",
        "VACUUM",
        "SELECT readfile('C:/Windows/win.ini')",
        "SELECT load_extension('evil')",
    ):
        response = _query(client, auth_headers, database_id, statement)
        assert response.status_code == 422, statement
        assert response.json()["error"]["code"] == "sql_error", statement

    multiple = _query(client, auth_headers, database_id, "SELECT 1; SELECT 2")
    assert multiple.status_code == 422
    assert multiple.json()["error"]["code"] == "sql_error"
    assert "one SQL statement at a time" in multiple.json()["error"]["message"]


def test_query_results_are_limited_and_blobs_are_labeled(
    client: TestClient, database_env: Path, auth_headers: dict[str, str]
) -> None:
    database = _create_database(client, auth_headers)
    database_id = database["id"]

    created = _query(
        client,
        auth_headers,
        database_id,
        "CREATE TABLE numbers (value INTEGER)",
    )
    assert created.status_code == 200

    inserted = _query(
        client,
        auth_headers,
        database_id,
        "WITH RECURSIVE counter(value) AS ("
        "SELECT 1 UNION ALL SELECT value + 1 FROM counter WHERE value < 250"
        ") INSERT INTO numbers (value) SELECT value FROM counter",
    )
    assert inserted.status_code == 200, inserted.text

    selected = _query(client, auth_headers, database_id, "SELECT value FROM numbers")
    assert selected.status_code == 200
    result = selected.json()
    assert result["truncated"] is True
    assert len(result["rows"]) == MAX_RESULT_ROWS

    blob = _query(client, auth_headers, database_id, "SELECT x'00ff' AS payload")
    assert blob.status_code == 200
    assert blob.json()["rows"] == [["<BLOB 2 bytes>"]]


def test_delete_removes_metadata_and_database_file(
    client: TestClient, database_env: Path, auth_headers: dict[str, str]
) -> None:
    database = _create_database(client, auth_headers)
    database_id = database["id"]
    path = _database_file(database_env, 1, database_id)
    assert path.is_file()

    created = _query(
        client, auth_headers, database_id, "CREATE TABLE items (id INTEGER)"
    )
    assert created.status_code == 200

    deleted = client.delete(f"/api/v1/databases/{database_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert not path.exists()
    assert client.get("/api/v1/databases", headers=auth_headers).json() == []

    gone = client.get(f"/api/v1/databases/{database_id}/tables", headers=auth_headers)
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "database_not_found"


def test_missing_database_file_reports_unavailable(
    client: TestClient, database_env: Path, auth_headers: dict[str, str]
) -> None:
    database = _create_database(client, auth_headers)
    database_id = database["id"]
    _database_file(database_env, 1, database_id).unlink()

    tables = client.get(f"/api/v1/databases/{database_id}/tables", headers=auth_headers)
    assert tables.status_code == 500
    assert tables.json()["error"]["code"] == "database_unavailable"

    queried = _query(client, auth_headers, database_id, "SELECT 1")
    assert queried.status_code == 500
    assert queried.json()["error"]["code"] == "database_unavailable"

    listed = client.get("/api/v1/databases", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "error"
    assert "missing" in listed.json()[0]["last_error"]
