from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import as_utc


class CreateDatabaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Database name is required.")
        if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
            raise ValueError("Database name cannot contain control characters.")
        return cleaned


class DatabaseOut(BaseModel):
    id: int
    name: str
    engine: str
    status: str
    table_count: int
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _dates_as_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class TableColumnOut(BaseModel):
    name: str
    type: str
    not_null: bool
    default_value: str | None
    primary_key: bool


class TableOut(BaseModel):
    name: str
    kind: str
    columns: list[TableColumnOut]


class ExecuteSqlRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50_000)

    @field_validator("sql")
    @classmethod
    def _clean_sql(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Enter a SQL statement to execute.")
        if "\x00" in cleaned:
            raise ValueError("SQL cannot contain null bytes.")
        return cleaned


class SqlResultOut(BaseModel):
    columns: list[str]
    rows: list[list[object]]
    rows_affected: int | None
    duration_ms: float
    truncated: bool
    statement_type: str
