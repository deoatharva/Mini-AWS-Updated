from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.storage import Bucket, StorageObject


def list_by_user(db: Session, user_id: int) -> list[Bucket]:
    return list(
        db.scalars(
            select(Bucket)
            .where(Bucket.user_id == user_id)
            .order_by(Bucket.created_at.desc(), Bucket.id.desc())
        )
    )


def get_by_id(db: Session, bucket_id: int) -> Bucket | None:
    return db.get(Bucket, bucket_id)


def get_by_name(db: Session, user_id: int, name: str) -> Bucket | None:
    return db.scalar(
        select(Bucket).where(Bucket.user_id == user_id, Bucket.name == name)
    )


def create(db: Session, *, user_id: int, name: str) -> Bucket:
    bucket = Bucket(user_id=user_id, name=name)
    db.add(bucket)
    db.flush()
    return bucket


def usage_by_bucket(db: Session, user_id: int) -> dict[int, tuple[int, int]]:
    rows = db.execute(
        select(
            StorageObject.bucket_id,
            func.count(StorageObject.id),
            func.coalesce(func.sum(StorageObject.size_bytes), 0),
        )
        .join(Bucket, Bucket.id == StorageObject.bucket_id)
        .where(Bucket.user_id == user_id)
        .group_by(StorageObject.bucket_id)
    ).all()
    return {int(bucket_id): (int(count), int(total)) for bucket_id, count, total in rows}
