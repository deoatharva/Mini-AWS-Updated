from sqlalchemy.orm import Session

from app.models.activity_event import ActivityEvent
from app.repositories import activity as activity_repo


def record(
    db: Session,
    *,
    user_id: int,
    service: str,
    action: str,
    resource_type: str,
    resource_id: int,
    resource_name: str,
) -> ActivityEvent:
    """Queue an activity event in the caller's transaction.

    The calling service commits it together with the resource change so the
    history never claims an action that did not persist.
    """
    return activity_repo.create(
        db,
        user_id=user_id,
        service=service,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
    )


def recent(db: Session, user_id: int, limit: int) -> list[ActivityEvent]:
    return activity_repo.list_recent(db, user_id, limit)
