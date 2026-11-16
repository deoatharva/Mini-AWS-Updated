import logging
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.storage.local_filesystem import (
    LocalFilesystemStorage,
    StorageAdapterError,
    UploadTooLargeError,
    UploadSource,
)
from app.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.permissions import ensure_owner
from app.models.storage import Bucket, StorageObject
from app.models.user import User
from app.repositories import buckets as bucket_repo
from app.repositories import storage_objects as object_repo
from app.schemas.storage import BucketOut, CreateBucketRequest
from app.services import activity_service
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

_INVALID_KEY_CHARACTERS = set('\\/:*?"<>|')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_CONTENT_TYPE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,63}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,63}$"
)


def _adapter() -> LocalFilesystemStorage:
    return LocalFilesystemStorage(settings.buckets_dir)


def _get_owned_bucket(db: Session, user: User, bucket_id: int) -> Bucket:
    bucket = bucket_repo.get_by_id(db, bucket_id)
    if bucket is None:
        raise NotFoundError("bucket_not_found", "Bucket not found.")
    ensure_owner(bucket, user)
    return bucket


def _bucket_out(
    bucket: Bucket, object_count: int = 0, total_bytes: int = 0
) -> BucketOut:
    return BucketOut(
        id=bucket.id,
        name=bucket.name,
        object_count=object_count,
        total_bytes=total_bytes,
        created_at=bucket.created_at,
    )


def _clean_object_key(filename: str | None) -> str:
    cleaned = (filename or "").strip()
    if not cleaned:
        raise ValidationError("invalid_object_key", "An object file name is required.")
    if len(cleaned) > 200:
        raise ValidationError(
            "invalid_object_key", "Object names must be 200 characters or fewer."
        )
    if cleaned in {".", ".."} or cleaned.startswith("."):
        raise ValidationError(
            "invalid_object_key", "Object names cannot start with a dot."
        )
    if cleaned.endswith((" ", ".")):
        raise ValidationError(
            "invalid_object_key", "Object names cannot end with a space or dot."
        )
    if any(character in _INVALID_KEY_CHARACTERS for character in cleaned):
        raise ValidationError(
            "invalid_object_key",
            'Object names cannot contain \\ / : * ? " < > |.',
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        raise ValidationError(
            "invalid_object_key", "Object names cannot contain control characters."
        )
    stem = cleaned.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED_NAMES:
        raise ValidationError(
            "invalid_object_key", "That object name is reserved by the operating system."
        )
    return cleaned


def _safe_content_type(value: str | None) -> str:
    candidate = (value or "").split(";", 1)[0].strip()
    if _CONTENT_TYPE_PATTERN.fullmatch(candidate):
        return candidate.lower()
    return "application/octet-stream"


def list_buckets(db: Session, user: User) -> list[BucketOut]:
    usage = bucket_repo.usage_by_bucket(db, user.id)
    return [
        _bucket_out(bucket, *usage.get(bucket.id, (0, 0)))
        for bucket in bucket_repo.list_by_user(db, user.id)
    ]


def create_bucket(
    db: Session, user: User, payload: CreateBucketRequest
) -> BucketOut:
    if bucket_repo.get_by_name(db, user.id, payload.name) is not None:
        raise ConflictError(
            "bucket_already_exists",
            "A bucket with that name already exists in your account.",
        )

    adapter = _adapter()
    bucket: Bucket | None = None
    try:
        bucket = bucket_repo.create(db, user_id=user.id, name=payload.name)
        adapter.ensure_bucket_directory(user.id, bucket.id)
        activity_service.record(
            db,
            user_id=user.id,
            service="storage",
            action="created",
            resource_type="bucket",
            resource_id=bucket.id,
            resource_name=bucket.name,
        )
        db.commit()
        db.refresh(bucket)
    except IntegrityError as exc:
        db.rollback()
        if bucket is not None:
            adapter.remove_bucket_directory(user.id, bucket.id)
        raise ConflictError(
            "bucket_already_exists",
            "A bucket with that name already exists in your account.",
        ) from exc
    except (StorageAdapterError, OSError) as exc:
        db.rollback()
        if bucket is not None:
            try:
                adapter.remove_bucket_directory(user.id, bucket.id)
            except StorageAdapterError:
                pass
        logger.exception("Could not create the bucket directory")
        raise AppError(
            500,
            "bucket_create_failed",
            "The bucket directory could not be created.",
        ) from exc

    return _bucket_out(bucket)


def delete_bucket(db: Session, user: User, bucket_id: int) -> None:
    bucket = _get_owned_bucket(db, user, bucket_id)
    object_count = object_repo.count_for_bucket(db, bucket.id)
    if object_count:
        raise ConflictError(
            "bucket_not_empty",
            f"Delete the {object_count} stored object(s) before deleting this bucket.",
        )

    adapter = _adapter()
    try:
        adapter.remove_bucket_directory(user.id, bucket.id)
    except StorageAdapterError as exc:
        logger.exception("Could not remove bucket directory %s", bucket.id)
        raise AppError(
            500,
            "bucket_delete_failed",
            "The bucket directory could not be removed.",
        ) from exc

    try:
        activity_service.record(
            db,
            user_id=user.id,
            service="storage",
            action="deleted",
            resource_type="bucket",
            resource_id=bucket.id,
            resource_name=bucket.name,
        )
        db.delete(bucket)
        db.commit()
    except Exception:
        db.rollback()
        try:
            adapter.ensure_bucket_directory(user.id, bucket.id)
        except StorageAdapterError:
            logger.exception("Could not restore bucket directory %s", bucket.id)
        raise


def list_objects(
    db: Session, user: User, bucket_id: int
) -> list[StorageObject]:
    bucket = _get_owned_bucket(db, user, bucket_id)
    return object_repo.list_for_bucket(db, bucket.id)


def upload_object(
    db: Session, user: User, bucket_id: int, upload_file: UploadSource
) -> StorageObject:
    bucket = _get_owned_bucket(db, user, bucket_id)
    object_key = _clean_object_key(getattr(upload_file, "filename", None))
    content_type = _safe_content_type(getattr(upload_file, "content_type", None))
    existing = object_repo.get_by_key(db, bucket.id, object_key)
    storage_name = uuid4().hex
    adapter = _adapter()
    try:
        bucket_dir = adapter.ensure_bucket_directory(user.id, bucket.id)
        size_bytes, etag = adapter.save_upload(
            bucket_dir,
            upload_file,
            storage_name,
            settings.max_upload_bytes,
        )
    except UploadTooLargeError as exc:
        limit = settings.max_upload_bytes
        if limit >= 1024 * 1024:
            message = f"Files must be at most {limit // (1024 * 1024)} MB."
        else:
            message = f"Files must be at most {limit} bytes."
        raise AppError(413, "file_too_large", message) from exc
    except StorageAdapterError as exc:
        logger.exception("Could not write uploaded object for bucket %s", bucket.id)
        raise AppError(
            500,
            "object_write_failed",
            "The uploaded file could not be saved.",
        ) from exc

    old_storage_name: str | None = None
    try:
        if existing is not None:
            old_storage_name = existing.storage_name
            existing.storage_name = storage_name
            existing.size_bytes = size_bytes
            existing.content_type = content_type
            existing.etag = etag
            existing.updated_at = utcnow()
            storage_object = existing
        else:
            storage_object = object_repo.create(
                db,
                bucket_id=bucket.id,
                object_key=object_key,
                storage_name=storage_name,
                size_bytes=size_bytes,
                content_type=content_type,
                etag=etag,
            )
        activity_service.record(
            db,
            user_id=user.id,
            service="storage",
            action="uploaded",
            resource_type="object",
            resource_id=storage_object.id,
            resource_name=f"{bucket.name}/{object_key}",
        )
        db.commit()
        db.refresh(storage_object)
    except Exception:
        db.rollback()
        try:
            adapter.remove_object(bucket_dir, storage_name)
        except StorageAdapterError:
            logger.exception("Could not clean up failed upload %s", storage_name)
        raise

    if old_storage_name and old_storage_name != storage_name:
        try:
            adapter.remove_object(bucket_dir, old_storage_name)
        except StorageAdapterError:
            logger.warning(
                "Could not remove the replaced object file for bucket %s", bucket.id
            )

    return storage_object


def get_object_file(
    db: Session, user: User, bucket_id: int, object_id: int
) -> tuple[StorageObject, Path]:
    bucket = _get_owned_bucket(db, user, bucket_id)
    storage_object = object_repo.get_by_id(db, bucket.id, object_id)
    if storage_object is None:
        raise NotFoundError("object_not_found", "Stored object not found.")

    adapter = _adapter()
    try:
        path = adapter.object_path(
            adapter.bucket_directory(user.id, bucket.id),
            storage_object.storage_name,
        )
    except StorageAdapterError as exc:
        raise AppError(
            500,
            "object_read_failed",
            "The stored object path could not be resolved.",
        ) from exc
    if not path.is_file():
        raise NotFoundError(
            "object_file_missing",
            "The stored file is missing from local storage.",
        )
    return storage_object, path


def delete_object(
    db: Session, user: User, bucket_id: int, object_id: int
) -> None:
    bucket = _get_owned_bucket(db, user, bucket_id)
    storage_object = object_repo.get_by_id(db, bucket.id, object_id)
    if storage_object is None:
        raise NotFoundError("object_not_found", "Stored object not found.")

    storage_name = storage_object.storage_name
    object_key = storage_object.object_key
    bucket_dir = _adapter().bucket_directory(user.id, bucket.id)
    activity_service.record(
        db,
        user_id=user.id,
        service="storage",
        action="deleted",
        resource_type="object",
        resource_id=storage_object.id,
        resource_name=f"{bucket.name}/{object_key}",
    )
    db.delete(storage_object)
    db.commit()
    try:
        _adapter().remove_object(bucket_dir, storage_name)
    except StorageAdapterError:
        logger.warning(
            "Could not remove object file %s for bucket %s", storage_name, bucket.id
        )
