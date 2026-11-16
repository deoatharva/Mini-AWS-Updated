import math
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

MAX_RESULT_ROWS = 200
_DISALLOWED_FIRST_KEYWORDS = {"attach", "detach", "pragma", "vacuum"}
_DISALLOWED_FUNCTIONS = {"load_extension", "readfile", "writefile"}
_DENIED_ACTIONS = {
    sqlite3.SQLITE_ATTACH,
    sqlite3.SQLITE_DETACH,
    sqlite3.SQLITE_PRAGMA,
    getattr(sqlite3, "SQLITE_CREATE_VTABLE", -1),
    getattr(sqlite3, "SQLITE_DROP_VTABLE", -1),
}


class DatabaseAdapterError(RuntimeError):
    """Raised when an isolated database file operation fails."""


class SQLExecutionError(RuntimeError):
    """Raised when a user SQL statement cannot be executed safely."""


@dataclass
class TableColumnInfo:
    name: str
    type: str
    not_null: bool
    default: str | None
    primary_key: bool


@dataclass
class TableInfo:
    name: str
    kind: str
    columns: list[TableColumnInfo]


@dataclass
class SQLResult:
    columns: list[str]
    rows: list[list[object]]
    rows_affected: int | None
    duration_ms: float
    truncated: bool
    statement_type: str


def _leading_keyword(sql: str) -> str:
    text = sql.lstrip()
    while text:
        if text.startswith("--"):
            newline = text.find("\n")
            text = "" if newline < 0 else text[newline + 1 :].lstrip()
            continue
        if text.startswith("/*"):
            end = text.find("*/", 2)
            text = "" if end < 0 else text[end + 2 :].lstrip()
            continue
        break
    match = re.match(r"[A-Za-z]+", text)
    return match.group(0).lower() if match else ""


def _authorizer(action: int, arg1: str | None, arg2: str | None, dbname, trigger) -> int:
    if action in _DENIED_ACTIONS and action >= 0:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in _DISALLOWED_FUNCTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return f"<BLOB {len(value)} bytes>"
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


class SQLiteDatabaseAdapter:
    """Owns per-resource SQLite files and restricts SQL file access."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _ensure_within_root(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise DatabaseAdapterError(
                "The database path escaped the data directory."
            ) from exc
        return resolved

    def database_path(self, user_id: int, database_id: int) -> Path:
        candidate = self.root / str(int(user_id)) / f"{int(database_id)}.sqlite3"
        return self._ensure_within_root(candidate)

    def _prepare_parent(self, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseAdapterError(
                "The database directory could not be created."
            ) from exc

    @contextmanager
    def _connection(
        self, path: Path, *, query_only: bool = False
    ) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(path, timeout=5.0)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA trusted_schema = OFF")
            if query_only:
                connection.execute("PRAGMA query_only = ON")
            yield connection
        finally:
            connection.close()

    def create_database(self, user_id: int, database_id: int) -> Path:
        path = self.database_path(user_id, database_id)
        if path.exists():
            raise DatabaseAdapterError("The database file already exists.")
        self._prepare_parent(path)
        try:
            with self._connection(path):
                pass
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        except sqlite3.Error as exc:
            path.unlink(missing_ok=True)
            raise DatabaseAdapterError("The local database file could not be created.") from exc
        return path

    def delete_database(self, user_id: int, database_id: int) -> None:
        path = self.database_path(user_id, database_id)
        try:
            for suffix in ("", "-journal", "-wal", "-shm"):
                Path(f"{path}{suffix}").unlink(missing_ok=True)
        except OSError as exc:
            raise DatabaseAdapterError("The database file could not be removed.") from exc

    def database_exists(self, user_id: int, database_id: int) -> bool:
        return self.database_path(user_id, database_id).is_file()

    def describe_tables(self, user_id: int, database_id: int) -> list[TableInfo]:
        path = self.database_path(user_id, database_id)
        if not path.is_file():
            raise DatabaseAdapterError("The local database file is missing.")
        try:
            with self._connection(path, query_only=True) as connection:
                rows = connection.execute(
                    "SELECT name, type FROM sqlite_master "
                    "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
                    "ORDER BY name"
                ).fetchall()
                tables: list[TableInfo] = []
                for name, kind in rows:
                    column_rows = connection.execute(
                        'SELECT name, type, "notnull", dflt_value, pk '
                        "FROM pragma_table_info(?) ORDER BY cid",
                        (name,),
                    ).fetchall()
                    tables.append(
                        TableInfo(
                            name=str(name),
                            kind=str(kind),
                            columns=[
                                TableColumnInfo(
                                    name=str(column_name),
                                    type=str(column_type or ""),
                                    not_null=bool(not_null),
                                    default=(
                                        str(default_value)
                                        if default_value is not None
                                        else None
                                    ),
                                    primary_key=bool(primary_key),
                                )
                                for (
                                    column_name,
                                    column_type,
                                    not_null,
                                    default_value,
                                    primary_key,
                                ) in column_rows
                            ],
                        )
                    )
                return tables
        except sqlite3.Error as exc:
            raise DatabaseAdapterError("The database schema could not be read.") from exc

    def execute_sql(self, user_id: int, database_id: int, sql: str) -> SQLResult:
        statement = sql.strip()
        if not statement:
            raise SQLExecutionError("Enter a SQL statement to execute.")
        first_keyword = _leading_keyword(statement)
        if first_keyword in _DISALLOWED_FIRST_KEYWORDS:
            raise SQLExecutionError(
                "ATTACH, DETACH, PRAGMA, and VACUUM are not allowed in isolated databases."
            )

        path = self.database_path(user_id, database_id)
        if not path.is_file():
            raise DatabaseAdapterError("The local database file is missing.")

        started = time.perf_counter()
        try:
            with self._connection(path) as connection:
                connection.set_authorizer(_authorizer)
                cursor = connection.execute(statement)
                columns = (
                    [description[0] for description in cursor.description]
                    if cursor.description
                    else []
                )
                rows: list[list[object]] = []
                truncated = False
                if columns:
                    fetched = cursor.fetchmany(MAX_RESULT_ROWS + 1)
                    truncated = len(fetched) > MAX_RESULT_ROWS
                    rows = [
                        [_json_value(value) for value in row]
                        for row in fetched[:MAX_RESULT_ROWS]
                    ]
                rows_affected = (
                    cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else None
                )
                connection.commit()
        except sqlite3.Error as exc:
            message = str(exc)
            if "not authorized" in message:
                message = "That SQL statement is not permitted in isolated databases."
            elif "one statement at a time" in message:
                message = "Run only one SQL statement at a time."
            raise SQLExecutionError(f"SQLite: {message}") from exc

        return SQLResult(
            columns=columns,
            rows=rows,
            rows_affected=rows_affected,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            truncated=truncated,
            statement_type=first_keyword.upper() or "SQL",
        )
