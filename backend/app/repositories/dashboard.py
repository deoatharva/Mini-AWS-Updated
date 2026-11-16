from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.application_deployment import ApplicationDeployment
from app.models.compute_instance import ComputeInstance
from app.models.database_resource import DatabaseResource
from app.models.storage import Bucket, StorageObject


def _status_counts(db: Session, model, user_id: int) -> tuple[int, int]:
    total, running = db.execute(
        select(
            func.count(model.id),
            func.coalesce(
                func.sum(case((model.status == "running", 1), else_=0)), 0
            ),
        ).where(model.user_id == user_id)
    ).one()
    return int(total or 0), int(running or 0)


def compute_counts(db: Session, user_id: int) -> tuple[int, int]:
    return _status_counts(db, ComputeInstance, user_id)


def application_counts(db: Session, user_id: int) -> tuple[int, int]:
    return _status_counts(db, ApplicationDeployment, user_id)


def bucket_count(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(Bucket.id)).where(Bucket.user_id == user_id)
        )
        or 0
    )


def object_totals(db: Session, user_id: int) -> tuple[int, int]:
    count, total_bytes = db.execute(
        select(
            func.count(StorageObject.id),
            func.coalesce(func.sum(StorageObject.size_bytes), 0),
        )
        .select_from(StorageObject)
        .join(Bucket, StorageObject.bucket_id == Bucket.id)
        .where(Bucket.user_id == user_id)
    ).one()
    return int(count or 0), int(total_bytes or 0)


def database_count(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(DatabaseResource.id)).where(
                DatabaseResource.user_id == user_id
            )
        )
        or 0
    )

