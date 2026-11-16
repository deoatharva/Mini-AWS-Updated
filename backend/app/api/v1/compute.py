from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.compute import (
    ComputeInstanceOut,
    CreateInstanceRequest,
    InstanceLogsOut,
)
from app.services import compute_service

router = APIRouter(prefix="/compute/instances", tags=["compute"])


@router.get("", response_model=list[ComputeInstanceOut])
def list_instances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ComputeInstanceOut]:
    instances = compute_service.list_instances(db, current_user)
    return [ComputeInstanceOut.model_validate(instance) for instance in instances]


@router.post("", response_model=ComputeInstanceOut, status_code=status.HTTP_201_CREATED)
def create_instance(
    payload: CreateInstanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComputeInstanceOut:
    instance = compute_service.create_instance(db, current_user, payload)
    return ComputeInstanceOut.model_validate(instance)


@router.get("/{instance_id}", response_model=ComputeInstanceOut)
def get_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComputeInstanceOut:
    instance = compute_service.get_instance(db, current_user, instance_id)
    return ComputeInstanceOut.model_validate(instance)


@router.post("/{instance_id}/start", response_model=ComputeInstanceOut)
def start_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComputeInstanceOut:
    instance = compute_service.start_instance(db, current_user, instance_id)
    return ComputeInstanceOut.model_validate(instance)


@router.post("/{instance_id}/stop", response_model=ComputeInstanceOut)
def stop_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComputeInstanceOut:
    instance = compute_service.stop_instance(db, current_user, instance_id)
    return ComputeInstanceOut.model_validate(instance)


@router.get("/{instance_id}/logs", response_model=InstanceLogsOut)
def get_instance_logs(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstanceLogsOut:
    content, truncated = compute_service.read_logs(db, current_user, instance_id)
    return InstanceLogsOut(content=content, truncated=truncated)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    compute_service.delete_instance(db, current_user, instance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
