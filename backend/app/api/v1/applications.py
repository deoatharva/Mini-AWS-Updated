from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.application import (
    ApplicationLogsOut,
    ApplicationOut,
    CreateApplicationRequest,
)
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApplicationOut]:
    deployments = application_service.list_deployments(db, current_user)
    return [ApplicationOut.model_validate(deployment) for deployment in deployments]


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: CreateApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    deployment = application_service.create_deployment(db, current_user, payload)
    return ApplicationOut.model_validate(deployment)


@router.get("/{deployment_id}", response_model=ApplicationOut)
def get_application(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    deployment = application_service.get_deployment(db, current_user, deployment_id)
    return ApplicationOut.model_validate(deployment)


@router.post("/{deployment_id}/start", response_model=ApplicationOut)
def start_application(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    deployment = application_service.start_deployment(db, current_user, deployment_id)
    return ApplicationOut.model_validate(deployment)


@router.post("/{deployment_id}/stop", response_model=ApplicationOut)
def stop_application(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    deployment = application_service.stop_deployment(db, current_user, deployment_id)
    return ApplicationOut.model_validate(deployment)


@router.get("/{deployment_id}/logs", response_model=ApplicationLogsOut)
def get_application_logs(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationLogsOut:
    content, truncated = application_service.read_logs(db, current_user, deployment_id)
    return ApplicationLogsOut(content=content, truncated=truncated)


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    application_service.delete_deployment(db, current_user, deployment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
