from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import as_utc


class CreateInstanceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Instance name is required.")
        if any(ord(character) < 32 for character in cleaned):
            raise ValueError("Instance name cannot contain control characters.")
        return cleaned


class ComputeInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    adapter: str
    status: str
    port: int | None
    pid: int | None
    local_url: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None

    @field_validator("created_at", "updated_at", "started_at", "stopped_at")
    @classmethod
    def _dates_as_utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value is not None else None


class InstanceLogsOut(BaseModel):
    content: str
    truncated: bool
