from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.storage import StorageObject


def list_for_bucket(db: Session, bucket_id: int) -> list[StorageObject]:
    return list(
        db.scalars(
            select(StorageObject)
            .where(StorageObject.bucket_id == bucket_id)
            .order_by(StorageObject.object_key.asc())
        )
    )


def count_for_bucket(db: Session, bucket_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(StorageObject.id)).where(
                StorageObject.bucket_id == bucket_id
            )
        )
        or 0
    )


def get_by_id(
    db: Session, bucket_id: int, object_id: int
) -> StorageObject | None:
    return db.scalar(
        select(StorageObject).where(
            StorageObject.bucket_id == bucket_id,
            StorageObject.id == object_id,
        )
    )


def get_by_key(
    db: Session, bucket_id: int, object_key: str
) -> StorageObject | None:
    return db.scalar(
        select(StorageObject).where(
            StorageObject.bucket_id == bucket_id,
            StorageObject.object_key == object_key,
        )
    )


def create(
    db: Session,
    *,
    bucket_id: int,
    object_key: str,
    storage_name: str,
    size_bytes: int,
    content_type: str,
    etag: str,
) -> StorageObject:
    storage_object = StorageObject(
        bucket_id=bucket_id,
        object_key=object_key,
        storage_name=storage_name,
        size_bytes=size_bytes,
        content_type=content_type,
        etag=etag,
    )
    db.add(storage_object)
    db.flush()
    return storage_object


def delete(db: Session, storage_object: StorageObject) -> None:
    db.delete(storage_object)
