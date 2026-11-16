from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.common import as_utc


class DashboardCountsOut(BaseModel):
    compute_total: int
    compute_running: int
    applications_total: int
    applications_running: int
    buckets_total: int
    objects_total: int
    storage_bytes: int
    databases_total: int


class ActivityItemOut(BaseModel):
    id: str
    service: str
    action: str
    resource_type: str
    resource_id: int
    resource_name: str
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def _timestamp_as_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class DashboardOut(BaseModel):
    counts: DashboardCountsOut
    recent_activity: list[ActivityItemOut]
