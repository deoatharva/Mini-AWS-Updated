#!/usr/bin/env python
"""Run the IAM-001 Section 13 workflow against a real uvicorn server.

This verification uses an isolated temporary data directory and SQLite
database, never the repository's real ``data/mini_aws.db``. It starts the real
FastAPI app, exercises owner and IAM authentication, enforces an allowed and a
denied API action, validates audit redaction and cross-account isolation, then
restarts the backend against the same database to prove persistence.

Run from the repository root with the backend virtual environment:

    .\\backend\\.venv\\Scripts\\python.exe .\\scripts\\verify_iam_e2e.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError as exc:  # pragma: no cover - diagnostic path
    raise SystemExit(
        "httpx is required. Run this script with backend\\.venv\\Scripts\\python.exe."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SERVER_PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
TEMP_ROOT = ROOT / ".pytest_cache" / "manual" / "iam-e2e"

OWNER_PASSWORD = "OwnerDemoPassword!2026"
TEMP_PASSWORD = "TemporaryStudentPassword!2026"
NEW_PASSWORD = "PermanentStudentPassword!2026"


class VerificationError(AssertionError):
    pass


def check(condition: bool, label: str) -> None:
    if not condition:
        raise VerificationError(label)
    print(f"[PASS] {label}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=20.0)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _error_code(response: httpx.Response) -> str | None:
    try:
        return response.json().get("error", {}).get("code")
    except (ValueError, AttributeError):
        return None


def _start_server(
    *,
    port: int,
    database_path: Path,
    data_dir: Path,
    secret_key: str,
    log_path: Path,
) -> tuple[subprocess.Popen[bytes], Any]:
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "development",
            "SECRET_KEY": secret_key,
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "DATA_DIR": str(data_dir),
            "API_HOST": "127.0.0.1",
            "API_PORT": str(port),
            "PYTHONUNBUFFERED": "1",
        }
    )
    log_file = log_path.open("ab")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [
            str(SERVER_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND,
        env=environment,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log_file.close()
            raise VerificationError(
                f"uvicorn exited early; inspect {log_path}"
            )
        try:
            with _client(base_url) as client:
                response = client.get("/api/v1/health")
            if response.status_code == 200:
                return process, log_file
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    process.terminate()
    log_file.close()
    raise VerificationError(f"uvicorn did not become healthy; inspect {log_path}")


def _stop_server(process: subprocess.Popen[bytes] | None, log_file: Any) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    if log_file is not None:
        log_file.close()


def _log_tail(path: Path, lines: int = 35) -> str:
    if not path.exists():
        return "(no server log)"
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def _assert_status(
    response: httpx.Response, expected: int, label: str
) -> dict | list | None:
    if response.status_code != expected:
        raise VerificationError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:500]}"
        )
    print(f"[PASS] {label} (HTTP {expected})")
    if not response.content:
        return None
    return response.json()


def run_demo(*, port: int, work_dir: Path, keep: bool) -> None:
    database_path = work_dir / "iam-e2e.db"
    data_dir = work_dir / "data"
    first_log = work_dir / "server-first.log"
    second_log = work_dir / "server-second.log"
    secret_key = secrets.token_urlsafe(48)
    base_url = f"http://127.0.0.1:{port}"
    email = f"owner-{uuid.uuid4().hex[:10]}@example.test"
    second_email = f"owner2-{uuid.uuid4().hex[:10]}@example.test"
    bucket_name = f"iam-demo-{uuid.uuid4().hex[:12]}"

    server: subprocess.Popen[bytes] | None = None
    server_log: Any = None
    owner_token = ""
    bucket_id: int | None = None
    failure: Exception | None = None

    try:
        server, server_log = _start_server(
            port=port,
            database_path=database_path,
            data_dir=data_dir,
            secret_key=secret_key,
            log_path=first_log,
        )
        print(f"[PASS] real uvicorn server started at {base_url}")

        with _client(base_url) as client:
            health = client.get("/api/v1/health")
            _assert_status(health, 200, "health endpoint")

            registered = _assert_status(
                client.post(
                    "/api/v1/auth/register",
                    json={
                        "name": "IAM Demo Owner",
                        "email": email,
                        "password": OWNER_PASSWORD,
                    },
                ),
                201,
                "owner registration",
            )
            assert isinstance(registered, dict)
            owner_token = registered["access_token"]
            account_id = registered["user"]["account"]["account_id"]
            owner_id = registered["user"]["id"]
            check(bool(re.fullmatch(r"\d{12}", account_id)), "owner has a 12-digit Local Account ID")
            check(
                "password" not in registered["user"]
                and "$2b$" not in json.dumps(registered),
                "registration response exposes no password or hash",
            )

            policies = _assert_status(
                client.get("/api/v1/iam/policies", headers=_headers(owner_token)),
                200,
                "owner lists IAM policies",
            )
            assert isinstance(policies, list)
            policy_by_name = {policy["name"]: policy for policy in policies}
            expected_policies = {
                "AdministratorAccess",
                "ReadOnlyAccess",
                "ComputeAccess",
                "StorageAccess",
                "DatabaseAccess",
                "IAMReadOnlyAccess",
                "IAMManagementAccess",
            }
            check(
                expected_policies <= set(policy_by_name),
                "all seven built-in policies are seeded",
            )
            check(
                all(policy["is_managed"] for policy in policies),
                "all seeded policies are marked built-in and immutable",
            )
            read_only_id = policy_by_name["ReadOnlyAccess"]["id"]

            created_user = _assert_status(
                client.post(
                    "/api/v1/iam/users",
                    headers=_headers(owner_token),
                    json={
                        "username": "student1",
                        "display_name": "Student One",
                        "console_access_enabled": True,
                        "password": TEMP_PASSWORD,
                        "confirm_password": TEMP_PASSWORD,
                        "must_change_password": True,
                        "group_ids": [],
                    },
                ),
                201,
                "owner creates IAM user student1",
            )
            assert isinstance(created_user, dict)
            student_id = created_user["id"]
            check(
                created_user["must_change_password"] is True
                and created_user["console_access_enabled"] is True,
                "student1 requires a first-login password change",
            )
            check(
                "password_hash" not in created_user
                and TEMP_PASSWORD not in json.dumps(created_user),
                "IAM user response exposes no credential material",
            )

            created_group = _assert_status(
                client.post(
                    "/api/v1/iam/groups",
                    headers=_headers(owner_token),
                    json={
                        "name": "TEST",
                        "description": "Read-only classroom demonstration group.",
                        "policy_ids": [read_only_id],
                    },
                ),
                201,
                "owner creates group TEST with ReadOnlyAccess",
            )
            assert isinstance(created_group, dict)
            group_id = created_group["id"]
            check(
                [policy["name"] for policy in created_group["policies"]]
                == ["ReadOnlyAccess"],
                "TEST group exposes its attached ReadOnlyAccess policy",
            )

            group_with_member = _assert_status(
                client.post(
                    f"/api/v1/iam/groups/{group_id}/users",
                    headers=_headers(owner_token),
                    json={"user_ids": [student_id]},
                ),
                200,
                "owner adds student1 to group TEST",
            )
            assert isinstance(group_with_member, dict)
            check(
                [member["username"] for member in group_with_member["members"]]
                == ["student1"],
                "student1 appears in the group member list",
            )

            student_detail = _assert_status(
                client.get(
                    f"/api/v1/iam/users/{student_id}",
                    headers=_headers(owner_token),
                ),
                200,
                "owner reads effective permissions for student1",
            )
            assert isinstance(student_detail, dict)
            check(
                "compute:ListInstances" in student_detail["effective_actions"],
                "ReadOnlyAccess grants compute:ListInstances",
            )
            check(
                "compute:CreateInstance" not in student_detail["effective_actions"]
                and "iam:ListUsers" not in student_detail["effective_actions"],
                "ReadOnlyAccess grants no create or IAM-management actions",
            )

            _assert_status(
                client.post("/api/v1/auth/logout", headers=_headers(owner_token)),
                204,
                "owner signs out and revokes the active session",
            )
            revoked = client.get("/api/v1/auth/me", headers=_headers(owner_token))
            check(revoked.status_code == 401, "signed-out owner token is rejected")

            iam_login = _assert_status(
                client.post(
                    "/api/v1/auth/iam/login",
                    json={
                        "account_id": account_id,
                        "username": "student1",
                        "password": TEMP_PASSWORD,
                    },
                ),
                200,
                "student1 signs in with Local Account ID and temporary password",
            )
            assert isinstance(iam_login, dict)
            student_token = iam_login["access_token"]
            check(
                iam_login["user"]["must_change_password"] is True,
                "IAM login reports the mandatory password change",
            )

            blocked_before_change = client.get(
                "/api/v1/compute/instances", headers=_headers(student_token)
            )
            check(
                blocked_before_change.status_code == 403
                and _error_code(blocked_before_change) == "password_change_required",
                "normal APIs are blocked before the mandatory password change",
            )

            changed = _assert_status(
                client.post(
                    "/api/v1/auth/change-password",
                    headers=_headers(student_token),
                    json={
                        "new_password": NEW_PASSWORD,
                        "confirm_password": NEW_PASSWORD,
                    },
                ),
                200,
                "student1 completes the mandatory password change",
            )
            assert isinstance(changed, dict)
            check(
                changed["must_change_password"] is False,
                "mandatory password flag clears after the change",
            )

            for path, label in (
                ("/api/v1/dashboard", "student1 can read the dashboard"),
                ("/api/v1/compute/instances", "student1 can list compute instances"),
                ("/api/v1/applications", "student1 can list applications"),
                ("/api/v1/storage/buckets", "student1 can list storage buckets"),
                ("/api/v1/databases", "student1 can list databases"),
            ):
                _assert_status(
                    client.get(path, headers=_headers(student_token)),
                    200,
                    label,
                )

            denied_actions = (
                (
                    client.post(
                        "/api/v1/compute/instances",
                        headers=_headers(student_token),
                        json={"name": "should-not-exist"},
                    ),
                    "ReadOnly user is denied compute:CreateInstance",
                ),
                (
                    client.post(
                        "/api/v1/storage/buckets",
                        headers=_headers(student_token),
                        json={"name": "should-not-exist"},
                    ),
                    "ReadOnly user is denied storage:CreateBucket",
                ),
                (
                    client.post(
                        "/api/v1/iam/users",
                        headers=_headers(student_token),
                        json={
                            "username": "should-not-exist",
                            "password": NEW_PASSWORD,
                            "confirm_password": NEW_PASSWORD,
                            "console_access_enabled": True,
                            "must_change_password": True,
                            "group_ids": [],
                        },
                    ),
                    "ReadOnly user is denied iam:CreateUser",
                ),
            )
            for response, label in denied_actions:
                check(
                    response.status_code == 403
                    and _error_code(response) == "access_denied",
                    label,
                )

            _assert_status(
                client.post("/api/v1/auth/logout", headers=_headers(student_token)),
                204,
                "student1 signs out",
            )
            old_password = client.post(
                "/api/v1/auth/iam/login",
                json={
                    "account_id": account_id,
                    "username": "student1",
                    "password": TEMP_PASSWORD,
                },
            )
            check(
                old_password.status_code == 401
                and old_password.json()["error"]["code"] == "invalid_credentials",
                "temporary password no longer works after the change",
            )
            new_password_login = _assert_status(
                client.post(
                    "/api/v1/auth/iam/login",
                    json={
                        "account_id": account_id,
                        "username": "student1",
                        "password": NEW_PASSWORD,
                    },
                ),
                200,
                "new password signs student1 in",
            )
            assert isinstance(new_password_login, dict)
            check(
                new_password_login["user"]["must_change_password"] is False,
                "new password session is not forced to change again",
            )

            owner_login = _assert_status(
                client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": OWNER_PASSWORD},
                ),
                200,
                "owner signs back in",
            )
            assert isinstance(owner_login, dict)
            owner_token = owner_login["access_token"]
            check(
                owner_login["user"]["account"]["account_id"] == account_id,
                "owner account context survives across sessions",
            )

            bucket = _assert_status(
                client.post(
                    "/api/v1/storage/buckets",
                    headers=_headers(owner_token),
                    json={"name": bucket_name},
                ),
                201,
                "owner creates a persisted storage resource",
            )
            assert isinstance(bucket, dict)
            bucket_id = bucket["id"]

            second_owner = _assert_status(
                client.post(
                    "/api/v1/auth/register",
                    json={
                        "name": "Other IAM Demo Owner",
                        "email": second_email,
                        "password": OWNER_PASSWORD,
                    },
                ),
                201,
                "a separate local account registers",
            )
            assert isinstance(second_owner, dict)
            second_token = second_owner["access_token"]
            second_account_id = second_owner["user"]["account"]["account_id"]
            check(second_account_id != account_id, "separate accounts have unique IDs")

            foreign_user = client.get(
                f"/api/v1/iam/users/{student_id}", headers=_headers(second_token)
            )
            check(
                foreign_user.status_code == 404,
                "cross-account IAM user lookup is rejected",
            )
            foreign_group = client.get(
                f"/api/v1/iam/groups/{group_id}", headers=_headers(second_token)
            )
            check(
                foreign_group.status_code == 404,
                "cross-account IAM group lookup is rejected",
            )
            second_buckets = _assert_status(
                client.get(
                    "/api/v1/storage/buckets", headers=_headers(second_token)
                ),
                200,
                "second account lists only its own storage",
            )
            assert isinstance(second_buckets, list)
            check(
                bucket_name not in {item["name"] for item in second_buckets},
                "cross-account storage resource is not visible",
            )
            foreign_delete = client.delete(
                f"/api/v1/storage/buckets/{bucket_id}",
                headers=_headers(second_token),
            )
            check(
                foreign_delete.status_code in {403, 404},
                "cross-account storage deletion is rejected",
            )
            same_username = _assert_status(
                client.post(
                    "/api/v1/iam/users",
                    headers=_headers(second_token),
                    json={
                        "username": "student1",
                        "display_name": "Other Student One",
                        "console_access_enabled": True,
                        "password": TEMP_PASSWORD,
                        "confirm_password": TEMP_PASSWORD,
                        "must_change_password": True,
                        "group_ids": [],
                    },
                ),
                201,
                "the same IAM username is allowed in a separate account",
            )
            check(
                isinstance(same_username, dict)
                and same_username["id"] != student_id,
                "duplicate usernames remain distinct account-scoped identities",
            )

            audit_logs = _assert_status(
                client.get(
                    "/api/v1/iam/audit-logs",
                    headers=_headers(owner_token),
                    params={"limit": 100},
                ),
                200,
                "owner lists account-scoped audit events",
            )
            assert isinstance(audit_logs, list)
            event_types = {entry["event_type"] for entry in audit_logs}
            expected_events = {
                "account.registered",
                "auth.signin_succeeded",
                "auth.signin_failed",
                "iam.user.created",
                "iam.group.created",
                "iam.policy.attached",
                "iam.group.member_added",
                "auth.password_changed",
            }
            check(
                expected_events <= event_types,
                "audit log contains required identity events",
            )
            check(
                all(entry["account_id"] == account_id for entry in audit_logs),
                "audit log is isolated to the owning account",
            )
            audit_json = json.dumps(audit_logs)
            check(
                TEMP_PASSWORD not in audit_json
                and NEW_PASSWORD not in audit_json
                and OWNER_PASSWORD not in audit_json
                and owner_token not in audit_json
                and new_password_login["access_token"] not in audit_json,
                "audit output contains no passwords or raw session tokens",
            )
            search = _assert_status(
                client.get(
                    "/api/v1/iam/audit-logs",
                    headers=_headers(owner_token),
                    params={"q": "student1", "success": "false", "limit": 100},
                ),
                200,
                "audit search filters failed student1 sign-in events",
            )
            assert isinstance(search, list)
            check(
                bool(search)
                and all(entry["success"] is False for entry in search),
                "failed sign-in filter returns real failed audit events",
            )

        _stop_server(server, server_log)
        server, server_log = None, None
        print("[PASS] first real-server phase stopped cleanly")

        server, server_log = _start_server(
            port=port,
            database_path=database_path,
            data_dir=data_dir,
            secret_key=secret_key,
            log_path=second_log,
        )
        print("[PASS] uvicorn restarted against the same SQLite database")

        with _client(base_url) as client:
            health = client.get("/api/v1/health")
            _assert_status(health, 200, "health endpoint after restart")

            owner_after_restart = _assert_status(
                client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": OWNER_PASSWORD},
                ),
                200,
                "owner signs in after restart",
            )
            assert isinstance(owner_after_restart, dict)
            owner_token = owner_after_restart["access_token"]
            check(
                owner_after_restart["user"]["account"]["account_id"] == account_id,
                "Local Account ID persists after restart",
            )

            persisted_user = _assert_status(
                client.get(
                    f"/api/v1/iam/users/{student_id}",
                    headers=_headers(owner_token),
                ),
                200,
                "IAM user persists after restart",
            )
            assert isinstance(persisted_user, dict)
            check(
                [group["name"] for group in persisted_user["groups"]] == ["TEST"]
                and "compute:ListInstances" in persisted_user["effective_actions"],
                "IAM user group membership and effective permissions persist",
            )
            persisted_group = _assert_status(
                client.get(
                    f"/api/v1/iam/groups/{group_id}",
                    headers=_headers(owner_token),
                ),
                200,
                "IAM group persists after restart",
            )
            assert isinstance(persisted_group, dict)
            check(
                [member["username"] for member in persisted_group["members"]]
                == ["student1"]
                and [policy["name"] for policy in persisted_group["policies"]]
                == ["ReadOnlyAccess"],
                "group members and policy attachments persist",
            )

            iam_after_restart = _assert_status(
                client.post(
                    "/api/v1/auth/iam/login",
                    json={
                        "account_id": account_id,
                        "username": "student1",
                        "password": NEW_PASSWORD,
                    },
                ),
                200,
                "student1 signs in with the permanent password after restart",
            )
            assert isinstance(iam_after_restart, dict)
            check(
                iam_after_restart["user"]["must_change_password"] is False,
                "completed password change persists after restart",
            )
            read_after_restart = client.get(
                "/api/v1/compute/instances",
                headers=_headers(iam_after_restart["access_token"]),
            )
            check(
                read_after_restart.status_code == 200,
                "read-only permission still works after restart",
            )
            _assert_status(
                client.post(
                    "/api/v1/auth/logout",
                    headers=_headers(iam_after_restart["access_token"]),
                ),
                204,
                "student1 session revokes after restart",
            )

            audit_after_restart = _assert_status(
                client.get(
                    "/api/v1/iam/audit-logs",
                    headers=_headers(owner_token),
                    params={"limit": 100},
                ),
                200,
                "audit log persists after restart",
            )
            assert isinstance(audit_after_restart, list)
            check(
                {entry["event_type"] for entry in audit_after_restart}
                >= {"iam.user.created", "iam.group.created", "auth.password_changed"},
                "required audit event history persists after restart",
            )

            buckets_after_restart = _assert_status(
                client.get(
                    "/api/v1/storage/buckets", headers=_headers(owner_token)
                ),
                200,
                "owner storage resources persist after restart",
            )
            assert isinstance(buckets_after_restart, list)
            check(
                bucket_name in {item["name"] for item in buckets_after_restart},
                "created bucket persists after restart",
            )

            if bucket_id is not None:
                _assert_status(
                    client.delete(
                        f"/api/v1/storage/buckets/{bucket_id}",
                        headers=_headers(owner_token),
                    ),
                    204,
                    "owner deletes the demonstration bucket",
                )
                bucket_id = None

        print("[PASS] IAM-001 Section 13 real-server demonstration completed")
        print(f"[INFO] isolated verification data: {work_dir}")
    except Exception as exc:  # noqa: BLE001 - report and clean up
        failure = exc
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        print("\n--- first server log tail ---", file=sys.stderr)
        print(_log_tail(first_log), file=sys.stderr)
        print("\n--- second server log tail ---", file=sys.stderr)
        print(_log_tail(second_log), file=sys.stderr)
    finally:
        _stop_server(server, server_log)
        if keep or failure is not None:
            print(f"[INFO] preserved verification directory: {work_dir}")
        else:
            shutil.rmtree(work_dir, ignore_errors=True)
            print("[PASS] temporary verification database and data removed")

    if failure is not None:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the temporary database/data directory after a successful run.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port for the temporary localhost server (default: choose a free port).",
    )
    args = parser.parse_args()

    if not SERVER_PYTHON.exists():
        raise SystemExit(
            "Backend virtual environment not found at backend/.venv. "
            "Run scripts/setup_windows.ps1 first."
        )
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    work_dir = TEMP_ROOT / f"run-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    work_dir.mkdir(parents=True)
    port = args.port or _free_port()
    try:
        run_demo(port=port, work_dir=work_dir, keep=args.keep)
    except KeyboardInterrupt:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
