"""Small forward migration for owner-only databases created before IAM.

The project intentionally uses ``create_all`` rather than Alembic. SQLite does
not add columns when a table already exists, so this module upgrades legacy
metadata in place and backfills one owner account per existing user before IAM
columns are used.
"""

from __future__ import annotations

import re
import secrets

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _owner_username(email: str | None) -> str:
    local = (email or "owner").split("@", 1)[0].strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", local).strip("-_")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"owner-{cleaned}".strip("-")
    cleaned = cleaned[:32]
    if len(cleaned) < 3:
        cleaned = (cleaned + "owner")[:32]
    return cleaned


def _new_account_id(connection) -> str:
    for _ in range(100):
        candidate = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
        exists = connection.execute(
            text("SELECT 1 FROM accounts WHERE account_id = :account_id"),
            {"account_id": candidate},
        ).first()
        if exists is None:
            return candidate
    raise RuntimeError("Could not allocate a unique local account ID.")


def _has_unique_account_username(inspector, table_name: str) -> bool:
    for entry in inspector.get_indexes(table_name):
        if entry.get("unique") and entry.get("column_names") == ["account_id", "username"]:
            return True
    for entry in inspector.get_unique_constraints(table_name):
        if entry.get("column_names") == ["account_id", "username"]:
            return True
    return False


def run_legacy_migrations(bind: Engine) -> None:
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("users")}
    additions = {
        "account_id": "INTEGER",
        "username": "TEXT",
        "user_type": "TEXT NOT NULL DEFAULT 'OWNER'",
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "console_access_enabled": "BOOLEAN NOT NULL DEFAULT 1",
        "must_change_password": "BOOLEAN NOT NULL DEFAULT 0",
        "updated_at": "DATETIME",
        "last_login_at": "DATETIME",
    }

    with bind.begin() as connection:
        for column, ddl in additions.items():
            if column not in column_names:
                connection.exec_driver_sql(
                    f"ALTER TABLE users ADD COLUMN {column} {ddl}"
                )

        # accounts is created by create_all before this function runs.
        rows = connection.execute(
            text(
                "SELECT id, name, email, created_at FROM users "
                "WHERE account_id IS NULL ORDER BY id"
            )
        ).mappings().all()
        for row in rows:
            public_id = _new_account_id(connection)
            account_name = f"{row['name']}'s local account"[:160]
            connection.execute(
                text(
                    "INSERT INTO accounts "
                    "(account_id, name, status, owner_user_id, created_at, updated_at) "
                    "VALUES (:public_id, :name, 'active', :owner_id, "
                    "COALESCE(:created_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)"
                ),
                {
                    "public_id": public_id,
                    "name": account_name,
                    "owner_id": row["id"],
                    "created_at": row["created_at"],
                },
            )
            account_pk = connection.execute(
                text("SELECT id FROM accounts WHERE account_id = :public_id"),
                {"public_id": public_id},
            ).scalar_one()
            connection.execute(
                text(
                    "UPDATE users SET account_id = :account_pk, username = :username, "
                    "user_type = 'OWNER', status = 'active', "
                    "console_access_enabled = 1, must_change_password = 0, "
                    "updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
                    "WHERE id = :user_id"
                ),
                {
                    "account_pk": account_pk,
                    "username": _owner_username(row["email"]),
                    "user_id": row["id"],
                },
            )

        # Existing databases created before IAM also lack the tenant link on
        # sessions. The ORM still resolves sessions through their user, but the
        # explicit account_id keeps the persisted data model tenant-aware.
        table_names = set(inspector.get_table_names())
        if "auth_sessions" in table_names:
            session_columns = {
                column["name"] for column in inspector.get_columns("auth_sessions")
            }
            if "account_id" not in session_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE auth_sessions ADD COLUMN account_id INTEGER "
                    "REFERENCES accounts(id) ON DELETE CASCADE"
                )
            connection.exec_driver_sql(
                "UPDATE auth_sessions SET account_id = ("
                "SELECT account_id FROM users WHERE users.id = auth_sessions.user_id"
                ") WHERE account_id IS NULL"
            )
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_auth_sessions_account_id "
                "ON auth_sessions (account_id)"
            )

        # New databases already have the model constraint. Legacy databases need
        # a unique index after usernames have been backfilled.
        if not _has_unique_account_username(inspector, "users"):
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_account_username "
                "ON users (account_id, username)"
            )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_users_account_id ON users (account_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)"
        )
