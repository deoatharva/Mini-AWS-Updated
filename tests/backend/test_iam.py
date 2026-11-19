from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.security import verify_password
from app.models.account import Account
from app.models.auth_session import AuthSession
from app.models.iam import AuditLog, GroupMembership, IamGroup, Policy
from app.models.user import User

PASSWORD = "correct-horse-battery-staple"
NEW_PASSWORD = "iam-first-login-new-password"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(
    client: TestClient,
    *,
    name: str = "Owner Student",
    email: str = "owner@example.com",
    password: str = PASSWORD,
):
    return client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def _owner_session(client: TestClient, email: str = "owner@example.com") -> dict:
    response = _register(client, email=email)
    assert response.status_code == 201, response.text
    return response.json()


def _policy_ids(client: TestClient, token: str) -> dict[str, int]:
    response = client.get("/api/v1/iam/policies", headers=_headers(token))
    assert response.status_code == 200, response.text
    return {policy["name"]: policy["id"] for policy in response.json()}


def _create_group(
    client: TestClient,
    token: str,
    name: str,
    *,
    policy_names: list[str] | None = None,
    description: str = "Test group",
):
    policy_ids = _policy_ids(client, token)
    return client.post(
        "/api/v1/iam/groups",
        headers=_headers(token),
        json={
            "name": name,
            "description": description,
            "policy_ids": [policy_ids[name] for name in (policy_names or [])],
        },
    )


def _create_user(
    client: TestClient,
    token: str,
    username: str = "student1",
    *,
    group_ids: list[int] | None = None,
    console_access_enabled: bool = True,
    must_change_password: bool = True,
    password: str = PASSWORD,
):
    return client.post(
        "/api/v1/iam/users",
        headers=_headers(token),
        json={
            "username": username,
            "display_name": f"{username.title()} Student",
            "console_access_enabled": console_access_enabled,
            "password": password,
            "confirm_password": password,
            "must_change_password": must_change_password,
            "group_ids": group_ids or [],
        },
    )


def _login_iam(
    client: TestClient,
    account_id: str,
    username: str = "student1",
    password: str = PASSWORD,
):
    return client.post(
        "/api/v1/auth/iam/login",
        json={
            "account_id": account_id,
            "username": username,
            "password": password,
        },
    )


def _complete_first_login(client: TestClient, token: str, password: str = NEW_PASSWORD):
    return client.post(
        "/api/v1/auth/change-password",
        headers=_headers(token),
        json={"new_password": password, "confirm_password": password},
    )


def test_registration_creates_owner_account_and_12_digit_id(
    client: TestClient, session_factory: sessionmaker
) -> None:
    first = _owner_session(client)
    second = _owner_session(client, email="owner2@example.com")

    first_account = first["user"]["account"]
    second_account = second["user"]["account"]
    assert len(first_account["account_id"]) == 12
    assert first_account["account_id"].isdigit()
    assert first_account["account_id"] != second_account["account_id"]
    assert first["user"]["user_type"] == "OWNER"
    assert first["user"]["account_id"] == first_account["id"]
    assert first["user"]["permissions"]
    assert "password_hash" not in first["user"]

    with session_factory() as db:
        account = db.scalar(
            select(Account).where(Account.account_id == first_account["account_id"])
        )
        owner = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert account is not None and owner is not None
        assert account.owner_user_id == owner.id
        assert owner.account_id == account.id
        assert owner.user_type == "OWNER"
        assert owner.username
        assert verify_password(PASSWORD, owner.password_hash)


def test_create_iam_user_hashes_password_and_scopes_username(
    client: TestClient, session_factory: sessionmaker
) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]

    created = _create_user(client, token)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["username"] == "student1"
    assert body["account_id"] == owner["user"]["account"]["account_id"]
    assert body["status"] == "active"
    assert body["console_access_enabled"] is True
    assert body["must_change_password"] is True
    assert body["groups"] == []
    assert "password" not in body
    assert "password_hash" not in body

    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "student1"))
        assert user is not None
        assert user.user_type == "IAM"
        assert user.password_hash != PASSWORD
        assert verify_password(PASSWORD, user.password_hash)
        assert user.email and user.email.endswith("@local.invalid")

    listed = client.get("/api/v1/iam/users", headers=_headers(token))
    assert listed.status_code == 200
    assert [user["username"] for user in listed.json()] == ["student1"]


def test_duplicate_username_is_account_scoped(client: TestClient) -> None:
    first_owner = _owner_session(client)
    second_owner = _owner_session(client, email="second@example.com")

    first = _create_user(client, first_owner["access_token"])
    duplicate = _create_user(client, first_owner["access_token"])
    other_account = _create_user(client, second_owner["access_token"])

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "username_already_exists"
    assert other_account.status_code == 201
    assert other_account.json()["account_id"] != first.json()["account_id"]


def test_iam_user_validation_and_generic_login_failures(client: TestClient) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]
    account_id = owner["user"]["account"]["account_id"]

    invalid_username = _create_user(client, token, username="Bad Name")
    mismatched = client.post(
        "/api/v1/iam/users",
        headers=_headers(token),
        json={
            "username": "student2",
            "password": PASSWORD,
            "confirm_password": "different-long-password",
            "must_change_password": True,
        },
    )

    assert invalid_username.status_code == 422
    assert mismatched.status_code == 422

    wrong_password = _login_iam(client, account_id, password="wrong-password")
    wrong_account = _login_iam(client, "999999999999", password=PASSWORD)
    unknown_user = client.post(
        "/api/v1/auth/iam/login",
        json={
            "account_id": account_id,
            "username": "missing-user",
            "password": PASSWORD,
        },
    )

    assert wrong_password.status_code == 401
    assert wrong_account.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["error"]["message"] == (
        "Invalid account ID, username, or password."
    )
    assert wrong_account.json()["error"]["message"] == (
        "Invalid account ID, username, or password."
    )


def test_disabled_console_and_deactivation_block_sign_in(
    client: TestClient,
) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]
    account_id = owner["user"]["account"]["account_id"]

    no_console = _create_user(
        client, token, username="noconsole", console_access_enabled=False
    )
    active = _create_user(client, token, username="activeuser")
    assert no_console.status_code == 201
    assert active.status_code == 201

    no_console_login = _login_iam(
        client, account_id, username="noconsole", password=PASSWORD
    )
    assert no_console_login.status_code == 401
    assert "Invalid account ID" in no_console_login.json()["error"]["message"]

    login = _login_iam(
        client, account_id, username="activeuser", password=PASSWORD
    )
    assert login.status_code == 200
    user_token = login.json()["access_token"]

    deactivated = client.patch(
        f"/api/v1/iam/users/{active.json()['id']}",
        headers=_headers(token),
        json={"status": "disabled", "console_access_enabled": False},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "disabled"
    assert deactivated.json()["console_access_enabled"] is False

    assert client.get("/api/v1/auth/me", headers=_headers(user_token)).status_code == 401
    assert (
        _login_iam(client, account_id, username="activeuser", password=PASSWORD).status_code
        == 401
    )


def test_first_login_forces_password_change_and_read_only_permissions(
    client: TestClient,
) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]
    account_id = owner["user"]["account"]["account_id"]

    group = _create_group(
        client, token, "TEST", policy_names=["ReadOnlyAccess"]
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]
    assert [policy["name"] for policy in group.json()["policies"]] == [
        "ReadOnlyAccess"
    ]

    created = _create_user(client, token, group_ids=[group_id])
    assert created.status_code == 201, created.text
    first_login = _login_iam(client, account_id)
    assert first_login.status_code == 200, first_login.text
    restricted_token = first_login.json()["access_token"]
    assert first_login.json()["user"]["must_change_password"] is True

    blocked = client.get(
        "/api/v1/compute/instances", headers=_headers(restricted_token)
    )
    me = client.get("/api/v1/auth/me", headers=_headers(restricted_token))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"
    assert me.status_code == 200
    assert "compute:ListInstances" in me.json()["permissions"]

    changed = _complete_first_login(client, restricted_token)
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False

    old_login = _login_iam(client, account_id)
    new_login = _login_iam(client, account_id, password=NEW_PASSWORD)
    assert old_login.status_code == 401
    assert new_login.status_code == 200, new_login.text
    user_token = new_login.json()["access_token"]

    assert (
        client.get("/api/v1/compute/instances", headers=_headers(user_token)).status_code
        == 200
    )
    assert (
        client.get("/api/v1/storage/buckets", headers=_headers(user_token)).status_code
        == 200
    )
    assert (
        client.get("/api/v1/applications", headers=_headers(user_token)).status_code
        == 200
    )
    assert client.get("/api/v1/databases", headers=_headers(user_token)).status_code == 200

    denied_create = client.post(
        "/api/v1/compute/instances",
        headers=_headers(user_token),
        json={"name": "Restricted instance"},
    )
    denied_bucket = client.post(
        "/api/v1/storage/buckets",
        headers=_headers(user_token),
        json={"name": "restricted-bucket"},
    )
    denied_iam = client.get("/api/v1/iam/users", headers=_headers(user_token))
    assert denied_create.status_code == 403
    assert denied_create.json()["error"]["code"] == "access_denied"
    assert denied_bucket.status_code == 403
    assert denied_iam.status_code == 403

    logout = client.post("/api/v1/auth/logout", headers=_headers(user_token))
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me", headers=_headers(user_token)).status_code == 401


def test_group_membership_and_policy_attachment_rules(client: TestClient) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]

    group = _create_group(
        client, token, "TEST", policy_names=["ReadOnlyAccess"]
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    duplicate_group = _create_group(client, token, "test")
    assert duplicate_group.status_code == 409
    assert duplicate_group.json()["error"]["code"] == "group_name_exists"

    user = _create_user(client, token)
    assert user.status_code == 201
    user_id = user.json()["id"]

    added = client.post(
        f"/api/v1/iam/groups/{group_id}/users",
        headers=_headers(token),
        json={"user_ids": [user_id]},
    )
    assert added.status_code == 200, added.text
    assert [member["username"] for member in added.json()["members"]] == ["student1"]

    duplicate_membership = client.post(
        f"/api/v1/iam/groups/{group_id}/users",
        headers=_headers(token),
        json={"user_ids": [user_id]},
    )
    assert duplicate_membership.status_code == 409
    assert duplicate_membership.json()["error"]["code"] == "membership_exists"

    policy_ids = _policy_ids(client, token)
    duplicate_attachment = client.post(
        f"/api/v1/iam/groups/{group_id}/policies",
        headers=_headers(token),
        json={"policy_ids": [policy_ids["ReadOnlyAccess"]]},
    )
    assert duplicate_attachment.status_code == 409
    assert duplicate_attachment.json()["error"]["code"] == "policy_attachment_exists"

    detached = client.delete(
        f"/api/v1/iam/groups/{group_id}/policies/{policy_ids['ReadOnlyAccess']}",
        headers=_headers(token),
    )
    assert detached.status_code == 200
    assert detached.json()["policies"] == []

    removed = client.delete(
        f"/api/v1/iam/groups/{group_id}/users/{user_id}", headers=_headers(token)
    )
    assert removed.status_code == 200
    assert removed.json()["members"] == []

    assert (
        client.delete(f"/api/v1/iam/groups/{group_id}", headers=_headers(token)).status_code
        == 204
    )
    still_exists = client.get(
        f"/api/v1/iam/users/{user_id}", headers=_headers(token)
    )
    assert still_exists.status_code == 200
    assert still_exists.json()["groups"] == []


def test_iam_management_cannot_modify_or_promote_self(client: TestClient) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]
    account_id = owner["user"]["account"]["account_id"]

    managers = _create_group(
        client, token, "Managers", policy_names=["IAMManagementAccess"]
    )
    manager_group_id = managers.json()["id"]
    manager = _create_user(
        client, token, username="manager1", group_ids=[manager_group_id]
    )
    assert manager.status_code == 201, manager.text
    manager_id = manager.json()["id"]

    login = _login_iam(client, account_id, username="manager1")
    assert login.status_code == 200
    manager_token = login.json()["access_token"]
    assert _complete_first_login(client, manager_token).status_code == 200

    patch_self = client.patch(
        f"/api/v1/iam/users/{manager_id}",
        headers=_headers(manager_token),
        json={"display_name": "Self Promoted"},
    )
    delete_self = client.delete(
        f"/api/v1/iam/users/{manager_id}", headers=_headers(manager_token)
    )
    assert patch_self.status_code == 403
    assert patch_self.json()["error"]["code"] == "cannot_modify_self"
    assert delete_self.status_code == 403

    second_group = _create_group(client, token, "Second Group")
    add_self = client.post(
        f"/api/v1/iam/groups/{second_group.json()['id']}/users",
        headers=_headers(manager_token),
        json={"user_ids": [manager_id]},
    )
    assert add_self.status_code == 403
    assert add_self.json()["error"]["code"] == "self_permission_escalation"

    policy_ids = _policy_ids(client, token)
    attach_admin_to_own_group = client.post(
        f"/api/v1/iam/groups/{manager_group_id}/policies",
        headers=_headers(manager_token),
        json={"policy_ids": [policy_ids["AdministratorAccess"]]},
    )
    assert attach_admin_to_own_group.status_code == 403
    assert (
        attach_admin_to_own_group.json()["error"]["code"]
        == "self_permission_escalation"
    )

    custom_policy = client.post(
        "/api/v1/iam/policies",
        headers=_headers(manager_token),
        json={
            "name": "SelfServiceAdmin",
            "description": "Would be an escalation",
            "actions": ["iam:AttachGroupPolicy"],
        },
    )
    audit = client.get("/api/v1/iam/audit-logs", headers=_headers(manager_token))
    assert custom_policy.status_code == 403
    assert audit.status_code == 403


def test_cross_account_resources_and_policies_are_isolated(
    client: TestClient,
) -> None:
    first = _owner_session(client)
    second = _owner_session(client, email="other@example.com")
    first_token = first["access_token"]
    second_token = second["access_token"]

    created_instance = client.post(
        "/api/v1/compute/instances",
        headers=_headers(first_token),
        json={"name": "First account instance"},
    )
    assert created_instance.status_code == 201
    instance_id = created_instance.json()["id"]
    first_group = _create_group(client, first_token, "First Group")
    group_id = first_group.json()["id"]

    denied_instance = client.get(
        f"/api/v1/compute/instances/{instance_id}", headers=_headers(second_token)
    )
    assert denied_instance.status_code == 403
    assert denied_instance.json()["error"]["code"] == "resource_forbidden"
    second_list = client.get(
        "/api/v1/compute/instances", headers=_headers(second_token)
    )
    assert second_list.status_code == 200
    assert second_list.json() == []
    denied_group = client.get(
        f"/api/v1/iam/groups/{group_id}", headers=_headers(second_token)
    )
    assert denied_group.status_code == 404

    custom = client.post(
        "/api/v1/iam/policies",
        headers=_headers(first_token),
        json={
            "name": "FirstCustom",
            "description": "Only the first account can see this.",
            "actions": ["compute:ListInstances"],
        },
    )
    assert custom.status_code == 201
    denied_policy = client.get(
        f"/api/v1/iam/policies/{custom.json()['id']}", headers=_headers(second_token)
    )
    assert denied_policy.status_code == 404


def test_custom_policy_lifecycle_and_managed_policy_protection(
    client: TestClient,
) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]
    policy_ids = _policy_ids(client, token)
    assert "AdministratorAccess" in policy_ids
    assert "ReadOnlyAccess" in policy_ids

    created = client.post(
        "/api/v1/iam/policies",
        headers=_headers(token),
        json={
            "name": "ViewComputeOnly",
            "description": "Allows listing compute instances only.",
            "actions": ["compute:ListInstances"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["is_managed"] is False
    assert body["actions"] == ["compute:ListInstances"]
    custom_id = body["id"]

    group = _create_group(
        client, token, "Custom Policy Group", policy_names=["ViewComputeOnly"]
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]

    in_use = client.delete(
        f"/api/v1/iam/policies/{custom_id}", headers=_headers(token)
    )
    builtin_patch = client.patch(
        f"/api/v1/iam/policies/{policy_ids['ReadOnlyAccess']}",
        headers=_headers(token),
        json={"description": "Changed built-in description"},
    )
    builtin_delete = client.delete(
        f"/api/v1/iam/policies/{policy_ids['ReadOnlyAccess']}",
        headers=_headers(token),
    )
    assert in_use.status_code == 409
    assert in_use.json()["error"]["code"] == "policy_in_use"
    assert builtin_patch.status_code == 409
    assert builtin_patch.json()["error"]["code"] == "managed_policy_immutable"
    assert builtin_delete.status_code == 409

    detach = client.delete(
        f"/api/v1/iam/groups/{group_id}/policies/{custom_id}",
        headers=_headers(token),
    )
    assert detach.status_code == 200
    deleted = client.delete(
        f"/api/v1/iam/policies/{custom_id}", headers=_headers(token)
    )
    assert deleted.status_code == 204


def test_audit_log_records_required_events_without_secrets(
    client: TestClient, session_factory: sessionmaker
) -> None:
    owner = _owner_session(client)
    token = owner["access_token"]
    account_id = owner["user"]["account"]["account_id"]
    group = _create_group(
        client, token, "Audit Group", policy_names=["ReadOnlyAccess"]
    )
    user = _create_user(client, token, group_ids=[group.json()["id"]])
    user_id = user.json()["id"]

    login = _login_iam(client, account_id)
    restricted = login.json()["access_token"]
    changed = _complete_first_login(client, restricted)
    assert changed.status_code == 200
    failed = _login_iam(client, account_id, password="wrong-password")
    assert failed.status_code == 401
    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    assert owner_login.status_code == 200

    reset = client.post(
        f"/api/v1/iam/users/{user_id}/reset-password",
        headers=_headers(token),
        json={
            "password": "reset-temporary-password",
            "confirm_password": "reset-temporary-password",
            "must_change_password": True,
        },
    )
    assert reset.status_code == 200
    removed = client.delete(
        f"/api/v1/iam/groups/{group.json()['id']}/users/{user_id}",
        headers=_headers(token),
    )
    assert removed.status_code == 200

    response = client.get("/api/v1/iam/audit-logs", headers=_headers(token))
    assert response.status_code == 200, response.text
    entries = response.json()
    events = {entry["event_type"] for entry in entries}
    assert {
        "iam.user.created",
        "iam.group.created",
        "iam.policy.attached",
        "iam.group.member_added",
        "iam.group.member_removed",
        "auth.signin_succeeded",
        "auth.signin_failed",
        "auth.password_changed",
        "auth.password_reset",
    }.issubset(events)
    assert all(entry["account_id"] == account_id for entry in entries)
    assert any(
        entry["event_type"] == "auth.signin_failed" and entry["success"] is False
        for entry in entries
    )
    assert any(entry["actor_type"] == "IAM" for entry in entries)
    assert any(entry["actor_type"] == "OWNER" for entry in entries)

    raw = response.text.lower()
    assert "correct-horse-battery-staple" not in raw
    assert "iam-first-login-new-password" not in raw
    assert "reset-temporary-password" not in raw
    assert "password_hash" not in raw
    assert "access_token" not in raw

    filtered = client.get(
        "/api/v1/iam/audit-logs?event_type=iam.user.created&success=true",
        headers=_headers(token),
    )
    assert filtered.status_code == 200
    assert filtered.json()
    assert {entry["event_type"] for entry in filtered.json()} == {"iam.user.created"}
    search = client.get(
        "/api/v1/iam/audit-logs?q=student1", headers=_headers(token)
    )
    assert search.status_code == 200
    assert search.json()
    metadata_search = client.get(
        "/api/v1/iam/audit-logs?q=student1&success=false", headers=_headers(token)
    )
    assert metadata_search.status_code == 200
    assert metadata_search.json()
    assert all(entry["success"] is False for entry in metadata_search.json())
    assert all("student1" in str(entry["metadata"]).lower() for entry in metadata_search.json())

    with session_factory() as db:
        audit_count = db.scalar(select(func.count()).select_from(AuditLog))
        membership_count = db.scalar(select(func.count()).select_from(GroupMembership))
        group_count = db.scalar(select(func.count()).select_from(IamGroup))
        policy_count = db.scalar(select(func.count()).select_from(Policy))
        session_count = db.scalar(select(func.count()).select_from(AuthSession))
    assert audit_count and audit_count > 0
    assert membership_count == 0
    assert group_count == 1
    assert policy_count == 7
    assert session_count and session_count > 0


def test_iam_login_throttling_is_applied(client: TestClient) -> None:
    for _ in range(5):
        response = _login_iam(client, "999999999999", password="wrong-password")
        assert response.status_code == 401
    throttled = _login_iam(client, "999999999999", password="wrong-password")
    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "login_throttled"


def test_iam_endpoints_require_authentication(client: TestClient) -> None:
    for path in (
        "/api/v1/iam/overview",
        "/api/v1/iam/users",
        "/api/v1/iam/groups",
        "/api/v1/iam/policies",
        "/api/v1/iam/audit-logs",
    ):
        response = client.get(path)
        assert response.status_code == 401
