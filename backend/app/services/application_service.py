import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.compute.process_adapter import ComputeAdapterError, WorkerInfo
from app.adapters.deployment.local_app_runner import LocalAppRunner
from app.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.permissions import ensure_owner
from app.models.application_deployment import ApplicationDeployment
from app.models.user import User
from app.repositories import application_deployments as deployment_repo
from app.schemas.application import CreateApplicationRequest
from app.services import activity_service
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"starting", "running", "stopping"}
STARTUP_GRACE_SECONDS = 20
STOP_RECOVERY_SECONDS = 20


def _adapter() -> LocalAppRunner:
    return LocalAppRunner(
        settings.applications_dir,
        settings.application_port_start,
        settings.application_port_end,
    )


def _get_owned(
    db: Session, user: User, deployment_id: int
) -> ApplicationDeployment:
    deployment = deployment_repo.get_by_id(db, deployment_id)
    if deployment is None:
        raise NotFoundError("application_not_found", "Application deployment not found.")
    ensure_owner(deployment, user)
    return deployment


def _age_seconds(value: datetime | None) -> float | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return (utcnow() - value).total_seconds()


def _started_at(info: WorkerInfo) -> datetime:
    try:
        parsed = datetime.fromisoformat(info.started_at.replace("Z", "+00:00"))
    except ValueError:
        return utcnow()
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _mark_error(deployment: ApplicationDeployment, message: str) -> None:
    deployment.status = "error"
    deployment.last_error = message[:1000]
    deployment.stopped_at = utcnow()
    deployment.updated_at = utcnow()


def _mark_stopped(deployment: ApplicationDeployment) -> None:
    deployment.status = "stopped"
    deployment.pid = None
    deployment.stopped_at = utcnow()
    deployment.last_error = None
    deployment.updated_at = utcnow()


def _refresh_deployment(
    deployment: ApplicationDeployment, adapter: LocalAppRunner
) -> bool:
    if deployment.status not in ACTIVE_STATUSES:
        return False

    info = adapter.read_worker_info(deployment.id)
    alive = (
        info is not None
        and adapter.is_process_alive(info.pid, deployment.id)
        and adapter.is_heartbeat_fresh(info)
    )

    if deployment.status == "stopping":
        if not alive:
            _mark_stopped(deployment)
            return True
        age = _age_seconds(deployment.updated_at)
        if age is not None and age > STOP_RECOVERY_SECONDS:
            try:
                stopped = adapter.stop(
                    deployment.id, info.pid if info else deployment.pid, timeout=2.0
                )
            except ComputeAdapterError:
                stopped = False
            if stopped:
                _mark_stopped(deployment)
            else:
                _mark_error(deployment, "The deployed app did not stop within the timeout.")
            return True
        return False

    if deployment.status == "starting":
        if (
            alive
            and info is not None
            and adapter.is_healthy(deployment.id, info.port)
        ):
            deployment.status = "running"
            deployment.pid = info.pid
            deployment.port = info.port
            deployment.started_at = _started_at(info)
            deployment.stopped_at = None
            deployment.last_error = None
            deployment.updated_at = utcnow()
            return True

        age = _age_seconds(deployment.updated_at)
        if age is not None and age > STARTUP_GRACE_SECONDS:
            _mark_error(deployment, "The deployed app did not become healthy in time.")
            return True
        return False

    if deployment.status == "running":
        if alive:
            return False
        _mark_error(deployment, "The deployed app process is no longer running.")
        return True

    return False


def list_deployments(db: Session, user: User) -> list[ApplicationDeployment]:
    adapter = _adapter()
    deployments = deployment_repo.list_by_user(db, user.id)
    changed = False
    for deployment in deployments:
        if _refresh_deployment(deployment, adapter):
            changed = True
    if changed:
        db.commit()
    return deployments


def get_deployment(
    db: Session, user: User, deployment_id: int
) -> ApplicationDeployment:
    deployment = _get_owned(db, user, deployment_id)
    if _refresh_deployment(deployment, _adapter()):
        db.commit()
    return deployment


def create_deployment(
    db: Session, user: User, payload: CreateApplicationRequest
) -> ApplicationDeployment:
    deployment = deployment_repo.create(db, user_id=user.id, name=payload.name)
    activity_service.record(
        db,
        user_id=user.id,
        service="applications",
        action="deployed",
        resource_type="application",
        resource_id=deployment.id,
        resource_name=deployment.name,
    )
    db.commit()
    db.refresh(deployment)
    return deployment


def start_deployment(
    db: Session, user: User, deployment_id: int
) -> ApplicationDeployment:
    deployment = _get_owned(db, user, deployment_id)
    adapter = _adapter()
    if _refresh_deployment(deployment, adapter):
        db.commit()

    if deployment.status in ACTIVE_STATUSES:
        raise ConflictError(
            "application_not_stopped",
            "This application is already starting, running, or stopping.",
        )

    adapter.stop(deployment.id, deployment.pid, timeout=2.0)

    deployment.status = "starting"
    deployment.last_error = None
    deployment.port = None
    deployment.pid = None
    deployment.started_at = None
    deployment.stopped_at = None
    deployment.updated_at = utcnow()
    db.commit()

    try:
        info = adapter.start(deployment.id, deployment.name)
    except ComputeAdapterError as exc:
        _mark_error(deployment, str(exc))
        activity_service.record(
            db,
            user_id=user.id,
            service="applications",
            action="failed",
            resource_type="application",
            resource_id=deployment.id,
            resource_name=deployment.name,
        )
        db.commit()
        raise ServiceUnavailableError(
            "application_start_failed",
            f"The application could not start: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected application start failure for deployment %s", deployment.id
        )
        _mark_error(deployment, "An unexpected error occurred while starting the app.")
        activity_service.record(
            db,
            user_id=user.id,
            service="applications",
            action="failed",
            resource_type="application",
            resource_id=deployment.id,
            resource_name=deployment.name,
        )
        db.commit()
        raise ServiceUnavailableError(
            "application_start_failed", "The application could not start."
        ) from exc

    deployment.status = "running"
    deployment.pid = info.pid
    deployment.port = info.port
    deployment.started_at = _started_at(info)
    deployment.stopped_at = None
    deployment.last_error = None
    deployment.updated_at = utcnow()
    activity_service.record(
        db,
        user_id=user.id,
        service="applications",
        action="started",
        resource_type="application",
        resource_id=deployment.id,
        resource_name=deployment.name,
    )
    db.commit()
    db.refresh(deployment)
    return deployment


def stop_deployment(
    db: Session, user: User, deployment_id: int
) -> ApplicationDeployment:
    deployment = _get_owned(db, user, deployment_id)
    adapter = _adapter()
    if _refresh_deployment(deployment, adapter):
        db.commit()

    if deployment.status == "stopped":
        return deployment

    deployment.status = "stopping"
    deployment.updated_at = utcnow()
    db.commit()

    try:
        stopped = adapter.stop(deployment.id, deployment.pid)
    except Exception:
        logger.exception(
            "Unexpected application stop failure for deployment %s", deployment.id
        )
        stopped = False

    if stopped:
        _mark_stopped(deployment)
        activity_service.record(
            db,
            user_id=user.id,
            service="applications",
            action="stopped",
            resource_type="application",
            resource_id=deployment.id,
            resource_name=deployment.name,
        )
        db.commit()
        db.refresh(deployment)
        return deployment

    _mark_error(deployment, "The deployed app did not stop within the timeout.")
    activity_service.record(
        db,
        user_id=user.id,
        service="applications",
        action="failed",
        resource_type="application",
        resource_id=deployment.id,
        resource_name=deployment.name,
    )
    db.commit()
    raise ServiceUnavailableError(
        "application_stop_failed",
        "The deployed app did not stop. Review the logs before trying again.",
    )


def delete_deployment(db: Session, user: User, deployment_id: int) -> None:
    deployment = _get_owned(db, user, deployment_id)
    adapter = _adapter()
    if _refresh_deployment(deployment, adapter):
        db.commit()

    try:
        stopped = adapter.stop(deployment.id, deployment.pid, timeout=4.0)
    except Exception:
        logger.exception(
            "Unexpected application cleanup failure for deployment %s", deployment.id
        )
        stopped = False
    if not stopped:
        _mark_error(deployment, "The deployed app could not be stopped before deletion.")
        db.commit()
        raise ServiceUnavailableError(
            "application_delete_failed",
            "The running app could not be stopped, so the deployment was not deleted.",
        )
    if deployment.status != "stopped":
        _mark_stopped(deployment)
        db.commit()

    try:
        adapter.remove(deployment.id)
    except OSError as exc:
        logger.exception("Could not remove files for deployment %s", deployment.id)
        raise AppError(
            500,
            "application_delete_failed",
            "The deployment files could not be removed.",
        ) from exc

    activity_service.record(
        db,
        user_id=user.id,
        service="applications",
        action="deleted",
        resource_type="application",
        resource_id=deployment.id,
        resource_name=deployment.name,
    )
    deployment_repo.delete(db, deployment)
    db.commit()


def read_logs(db: Session, user: User, deployment_id: int) -> tuple[str, bool]:
    deployment = get_deployment(db, user, deployment_id)
    return _adapter().read_logs(deployment.id)


def stop_all_active(db: Session) -> None:
    """Best-effort cleanup of managed app workers during API shutdown."""
    adapter = _adapter()
    deployments = deployment_repo.list_active(db)
    for deployment in deployments:
        try:
            info = adapter.read_worker_info(deployment.id)
            pid = info.pid if info is not None else deployment.pid
            if adapter.stop(deployment.id, pid, timeout=3.0):
                _mark_stopped(deployment)
            else:
                _mark_error(deployment, "The app did not stop during API shutdown.")
        except Exception:
            logger.exception(
                "Could not stop deployed app %s during shutdown", deployment.id
            )
            _mark_error(deployment, "The app could not be stopped during API shutdown.")
    if deployments:
        db.commit()
