from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity_event import ActivityEvent


def create(
    db: Session,
    *,
    user_id: int,
    service: str,
    action: str,
    resource_type: str,
    resource_id: int,
    resource_name: str,
) -> ActivityEvent:
    event = ActivityEvent(
        user_id=user_id,
        service=service,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
    )
    db.add(event)
    db.flush()
    return event


def list_recent(db: Session, user_id: int, limit: int) -> list[ActivityEvent]:
    return list(
        db.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
            .limit(limit)
        )
    )
