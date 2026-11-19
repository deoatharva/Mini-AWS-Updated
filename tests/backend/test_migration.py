import sqlite3

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database.session import init_db


def test_legacy_owner_database_is_backfilled_idempotently(tmp_path) -> None:
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE auth_sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        );
        CREATE TABLE compute_instances (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(80) NOT NULL,
            adapter VARCHAR(20) NOT NULL DEFAULT 'process',
            status VARCHAR(20) NOT NULL DEFAULT 'stopped',
            port INTEGER,
            pid INTEGER,
            last_error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME,
            stopped_at DATETIME
        );
        INSERT INTO users (id, name, email, password_hash, created_at)
        VALUES (7, 'Legacy Student', 'legacy.student@example.com', 'hash', '2026-01-02 03:04:05');
        INSERT INTO users (id, name, email, password_hash, created_at)
        VALUES (8, 'Numeric Local', '12345@example.com', 'hash', '2026-01-03 03:04:05');
        INSERT INTO auth_sessions (id, user_id, token_hash, expires_at)
        VALUES (21, 7, 'legacy-token-hash', '2099-01-01 00:00:00');
        INSERT INTO compute_instances (id, user_id, name, status)
        VALUES (11, 7, 'Preserved instance', 'stopped');
        """
    )
    connection.commit()
    connection.close()

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    init_db(engine)
    init_db(engine)

    with Session(engine) as db:
        users = db.execute(
            text(
                "SELECT id, account_id, username, user_type, status, "
                "console_access_enabled, must_change_password FROM users ORDER BY id"
            )
        ).mappings().all()
        accounts = db.execute(
            text(
                "SELECT id, account_id, owner_user_id, status FROM accounts "
                "ORDER BY id"
            )
        ).mappings().all()
        instance = db.execute(
            text("SELECT user_id, name FROM compute_instances WHERE id = 11")
        ).mappings().one()
        policy_count = db.execute(text("SELECT COUNT(*) FROM policies")).scalar_one()
        session_row = db.execute(
            text("SELECT user_id, account_id FROM auth_sessions WHERE id = 21")
        ).mappings().one()

    assert len(users) == 2
    assert len(accounts) == 2
    assert len({account["account_id"] for account in accounts}) == 2
    assert all(len(account["account_id"]) == 12 for account in accounts)
    assert {account["owner_user_id"] for account in accounts} == {7, 8}
    assert {account["status"] for account in accounts} == {"active"}

    by_id = {user["id"]: user for user in users}
    assert by_id[7]["username"] == "legacy-student"
    assert by_id[8]["username"] == "owner-12345"
    assert {user["user_type"] for user in users} == {"OWNER"}
    assert {user["status"] for user in users} == {"active"}
    assert all(user["console_access_enabled"] == 1 for user in users)
    assert all(user["must_change_password"] == 0 for user in users)
    assert {user["account_id"] for user in users} == {account["id"] for account in accounts}
    assert instance == {"user_id": 7, "name": "Preserved instance"}
    assert policy_count == 7
    assert session_row["user_id"] == 7
    assert session_row["account_id"] == by_id[7]["account_id"]

    engine.dispose()
