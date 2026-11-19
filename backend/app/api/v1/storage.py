from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.database.session import get_db
from app.models.user import User
from app.schemas.storage import (
    BucketOut,
    CreateBucketRequest,
    StorageObjectOut,
)
from app.services import storage_service

router = APIRouter(prefix="/storage/buckets", tags=["storage"])


@router.get("", response_model=list[BucketOut])
def list_buckets(
    current_user: User = Depends(require_permission("storage:ListBuckets")),
    db: Session = Depends(get_db),
) -> list[BucketOut]:
    return storage_service.list_buckets(db, current_user)


@router.post("", response_model=BucketOut, status_code=status.HTTP_201_CREATED)
def create_bucket(
    payload: CreateBucketRequest,
    current_user: User = Depends(require_permission("storage:CreateBucket")),
    db: Session = Depends(get_db),
) -> BucketOut:
    return storage_service.create_bucket(db, current_user, payload)


@router.delete("/{bucket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bucket(
    bucket_id: int,
    current_user: User = Depends(require_permission("storage:DeleteBucket")),
    db: Session = Depends(get_db),
) -> Response:
    storage_service.delete_bucket(db, current_user, bucket_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{bucket_id}/objects", response_model=list[StorageObjectOut])
def list_objects(
    bucket_id: int,
    current_user: User = Depends(require_permission("storage:ListObjects")),
    db: Session = Depends(get_db),
) -> list[StorageObjectOut]:
    objects = storage_service.list_objects(db, current_user, bucket_id)
    return [StorageObjectOut.model_validate(item) for item in objects]


@router.post(
    "/{bucket_id}/objects",
    response_model=StorageObjectOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_object(
    bucket_id: int,
    upload_file: UploadFile = File(..., alias="file"),
    current_user: User = Depends(require_permission("storage:UploadObject")),
    db: Session = Depends(get_db),
) -> StorageObjectOut:
    storage_object = storage_service.upload_object(
        db, current_user, bucket_id, upload_file
    )
    return StorageObjectOut.model_validate(storage_object)


@router.get("/{bucket_id}/objects/{object_id}/download")
def download_object(
    bucket_id: int,
    object_id: int,
    current_user: User = Depends(require_permission("storage:DownloadObject")),
    db: Session = Depends(get_db),
) -> FileResponse:
    storage_object, path = storage_service.get_object_file(
        db, current_user, bucket_id, object_id
    )
    return FileResponse(
        path,
        media_type=storage_object.content_type,
        filename=storage_object.object_key,
        headers={"ETag": f'"{storage_object.etag}"'},
    )


@router.delete(
    "/{bucket_id}/objects/{object_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_object(
    bucket_id: int,
    object_id: int,
    current_user: User = Depends(require_permission("storage:DeleteObject")),
    db: Session = Depends(get_db),
) -> Response:
    storage_service.delete_object(db, current_user, bucket_id, object_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
