from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_session_token, verify_password
from app.models.auth_session import AuthSession
from app.models.user import User
from app.utils.time import utcnow

PASSWORD = "correct-horse-battery-staple"


def _register(
    client: TestClient,
    *,
    name: str = "Local User",
    email: str = "user@example.com",
    password: str = PASSWORD,
):
    return client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_token_and_safe_user(
    client: TestClient, session_factory: sessionmaker
) -> None:
    response = _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["name"] == "Local User"
    assert body["user"]["email"] == "user@example.com"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00")).tzinfo
    assert datetime.fromisoformat(body["user"]["created_at"].replace("Z", "+00:00")).tzinfo

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        stored_session = db.scalar(select(AuthSession))

    assert user is not None
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$2")
    assert verify_password(PASSWORD, user.password_hash) is True
    assert stored_session is not None
    assert stored_session.token_hash != body["access_token"]
    assert stored_session.token_hash == hash_session_token(body["access_token"])


def test_register_normalizes_email_and_rejects_duplicates(client: TestClient) -> None:
    first = _register(client, email="  User@Example.COM ")
    assert first.status_code == 201
    assert first.json()["user"]["email"] == "user@example.com"

    duplicate = _register(client, email="USER@example.com")

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_already_registered"


def test_register_validation_errors_use_error_envelope(client: TestClient) -> None:
    short_password = _register(client, password="too-short")
    assert short_password.status_code == 422
    body = short_password.json()["error"]
    assert body["code"] == "validation_error"
    assert any(detail["field"] == "password" for detail in body["details"])

    bad_email = _register(client, email="not-an-email")
    assert bad_email.status_code == 422
    assert any(
        detail["field"] == "email" for detail in bad_email.json()["error"]["details"]
    )

    blank_name = _register(client, name="   ")
    assert blank_name.status_code == 422


def test_login_success_and_generic_invalid_credentials(client: TestClient) -> None:
    _register(client)

    success = client.post(
        "/api/v1/auth/login",
        json={"email": "USER@example.com", "password": PASSWORD},
    )
    assert success.status_code == 200
    assert success.json()["access_token"]
    assert success.json()["user"]["email"] == "user@example.com"

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )
    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": PASSWORD},
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["error"]["code"] == "invalid_credentials"
    assert (
        wrong_password.json()["error"]["message"]
        == unknown_user.json()["error"]["message"]
    )


def test_me_requires_a_valid_session(client: TestClient) -> None:
    missing = client.get("/api/v1/auth/me")
    garbage = client.get("/api/v1/auth/me", headers=_auth_headers("not-a-token"))

    registered = _register(client)
    token = registered.json()["access_token"]
    valid = client.get("/api/v1/auth/me", headers=_auth_headers(token))

    assert missing.status_code == 401
    assert garbage.status_code == 401
    assert garbage.json()["error"]["code"] == "invalid_token"
    assert valid.status_code == 200
    assert valid.json()["email"] == "user@example.com"


def test_logout_invalidates_the_session(
    client: TestClient, session_factory: sessionmaker
) -> None:
    token = _register(client).json()["access_token"]

    logout = client.post("/api/v1/auth/logout", headers=_auth_headers(token))
    after_logout = client.get("/api/v1/auth/me", headers=_auth_headers(token))

    assert logout.status_code == 204
    assert after_logout.status_code == 401
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_update_profile_changes_display_name(client: TestClient) -> None:
    token = _register(client).json()["access_token"]

    response = client.patch(
        "/api/v1/auth/me",
        json={"name": "  Updated Student  "},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Student"
    assert response.json()["email"] == "user@example.com"

    me = client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert me.json()["name"] == "Updated Student"

    blank = client.patch(
        "/api/v1/auth/me", json={"name": "   "}, headers=_auth_headers(token)
    )
    anonymous = client.patch("/api/v1/auth/me", json={"name": "Another"})

    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"
    assert anonymous.status_code == 401


def test_change_password_verifies_current_password_without_sign_out(
    client: TestClient, session_factory: sessionmaker
) -> None:
    token = _register(client).json()["access_token"]

    wrong = client.post(
        "/api/v1/auth/password",
        json={"current_password": "not-my-password", "new_password": "a-new-long-password"},
        headers=_auth_headers(token),
    )
    same = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=_auth_headers(token),
    )
    short = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "too-short"},
        headers=_auth_headers(token),
    )

    assert wrong.status_code == 422
    assert wrong.json()["error"]["code"] == "invalid_current_password"
    assert same.status_code == 422
    assert same.json()["error"]["code"] == "password_unchanged"
    assert short.status_code == 422
    assert short.json()["error"]["code"] == "validation_error"

    still_valid = client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert still_valid.status_code == 200

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert verify_password(PASSWORD, user.password_hash)


def test_change_password_revokes_other_sessions(
    client: TestClient, session_factory: sessionmaker
) -> None:
    token = _register(client).json()["access_token"]
    other_token = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": PASSWORD},
    ).json()["access_token"]
    new_password = "a-completely-new-password"

    response = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": new_password},
        headers=_auth_headers(token),
    )

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me", headers=_auth_headers(token)).status_code == 200
    assert (
        client.get("/api/v1/auth/me", headers=_auth_headers(other_token)).status_code
        == 401
    )

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": PASSWORD},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": new_password},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert verify_password(new_password, user.password_hash)
        assert not verify_password(PASSWORD, user.password_hash)


def test_expired_session_is_rejected_and_removed(
    client: TestClient, session_factory: sessionmaker
) -> None:
    token = _register(client).json()["access_token"]

    with session_factory() as db:
        stored_session = db.scalar(select(AuthSession))
        assert stored_session is not None
        stored_session.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    response = client.get("/api/v1/auth/me", headers=_auth_headers(token))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_expired"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 0
