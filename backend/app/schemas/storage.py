import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import as_utc

BUCKET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")


class CreateBucketRequest(BaseModel):
    name: str = Field(min_length=1, max_length=63)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not 3 <= len(cleaned) <= 63:
            raise ValueError("Bucket names must be between 3 and 63 characters.")
        if ".." in cleaned:
            raise ValueError("Bucket names cannot contain consecutive dots.")
        if not BUCKET_NAME_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Use lowercase letters, numbers, dots, and hyphens; "
                "start and end with a letter or number."
            )
        return cleaned


class BucketOut(BaseModel):
    id: int
    name: str
    object_count: int = 0
    total_bytes: int = 0
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _created_at_as_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class StorageObjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bucket_id: int
    object_key: str
    size_bytes: int
    content_type: str
    etag: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _dates_as_utc(cls, value: datetime) -> datetime:
        return as_utc(value)
