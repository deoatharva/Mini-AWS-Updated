from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database_resource import DatabaseResource


def list_by_user(db: Session, user_id: int) -> list[DatabaseResource]:
    return list(
        db.scalars(
            select(DatabaseResource)
            .where(DatabaseResource.user_id == user_id)
            .order_by(DatabaseResource.created_at.desc(), DatabaseResource.id.desc())
        )
    )


def get_by_id(db: Session, database_id: int) -> DatabaseResource | None:
    return db.get(DatabaseResource, database_id)


def get_by_name(
    db: Session, user_id: int, name: str
) -> DatabaseResource | None:
    return db.scalar(
        select(DatabaseResource).where(
            DatabaseResource.user_id == user_id,
            func.lower(DatabaseResource.name) == name.lower(),
        )
    )


def create(db: Session, *, user_id: int, name: str) -> DatabaseResource:
    resource = DatabaseResource(user_id=user_id, name=name)
    db.add(resource)
    db.flush()
    return resource
