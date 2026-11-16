from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import dashboard as dashboard_repo
from app.schemas.common import as_utc
from app.schemas.dashboard import (
    ActivityItemOut,
    DashboardCountsOut,
    DashboardOut,
)
from app.services import activity_service, application_service, compute_service

ACTIVITY_LIMIT = 10


def get_dashboard(db: Session, user: User) -> DashboardOut:
    # Refresh managed process states so counts reflect reality.
    compute_service.list_instances(db, user)
    application_service.list_deployments(db, user)

    compute_total, compute_running = dashboard_repo.compute_counts(db, user.id)
    applications_total, applications_running = dashboard_repo.application_counts(
        db, user.id
    )
    buckets_total = dashboard_repo.bucket_count(db, user.id)
    objects_total, storage_bytes = dashboard_repo.object_totals(db, user.id)
    databases_total = dashboard_repo.database_count(db, user.id)

    counts = DashboardCountsOut(
        compute_total=compute_total,
        compute_running=compute_running,
        applications_total=applications_total,
        applications_running=applications_running,
        buckets_total=buckets_total,
        objects_total=objects_total,
        storage_bytes=storage_bytes,
        databases_total=databases_total,
    )

    recent_activity = [
        ActivityItemOut(
            id=f"activity-{event.id}",
            service=event.service,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            resource_name=event.resource_name,
            timestamp=as_utc(event.created_at),
        )
        for event in activity_service.recent(db, user.id, ACTIVITY_LIMIT)
    ]

    return DashboardOut(counts=counts, recent_activity=recent_activity)
