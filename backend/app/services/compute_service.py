import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.compute.process_adapter import (
    ComputeAdapterError,
    ProcessComputeAdapter,
    WorkerInfo,
)
from app.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.permissions import account_owner_user_id, ensure_owner
from app.models.compute_instance import ComputeInstance
from app.models.user import User
from app.repositories import compute_instances as instance_repo
from app.schemas.compute import CreateInstanceRequest
from app.services import activity_service
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"starting", "running", "stopping"}
STARTUP_GRACE_SECONDS = 20
STOP_RECOVERY_SECONDS = 20


def _adapter() -> ProcessComputeAdapter:
    return ProcessComputeAdapter(
        settings.instances_dir,
        settings.compute_port_start,
        settings.compute_port_end,
    )


def _get_owned(db: Session, user: User, instance_id: int) -> ComputeInstance:
    instance = instance_repo.get_by_id(db, instance_id)
    if instance is None:
        raise NotFoundError("instance_not_found", "Compute instance not found.")
    ensure_owner(instance, user)
    return instance


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


def _mark_error(instance: ComputeInstance, message: str) -> None:
    instance.status = "error"
    instance.last_error = message[:1000]
    instance.stopped_at = utcnow()
    instance.updated_at = utcnow()


def _mark_stopped(instance: ComputeInstance) -> None:
    instance.status = "stopped"
    instance.pid = None
    instance.stopped_at = utcnow()
    instance.last_error = None
    instance.updated_at = utcnow()


def _refresh_instance(
    db: Session, instance: ComputeInstance, adapter: ProcessComputeAdapter
) -> bool:
    """Reconcile persisted metadata with the real worker process and heartbeat."""
    if instance.status not in ACTIVE_STATUSES:
        return False

    info = adapter.read_worker_info(instance.id)
    alive = (
        info is not None
        and adapter.is_process_alive(info.pid, instance.id)
        and adapter.is_heartbeat_fresh(info)
    )

    if instance.status == "stopping":
        if not alive:
            _mark_stopped(instance)
            return True

        age = _age_seconds(instance.updated_at)
        if age is not None and age > STOP_RECOVERY_SECONDS:
            try:
                stopped = adapter.stop(instance.id, info.pid if info else instance.pid, timeout=2.0)
            except ComputeAdapterError:
                stopped = False
            if stopped:
                _mark_stopped(instance)
            else:
                _mark_error(instance, "The local worker did not stop within the timeout.")
            return True
        return False

    if instance.status == "starting":
        if (
            alive
            and info is not None
            and adapter.is_healthy(instance.id, info.port)
        ):
            instance.status = "running"
            instance.pid = info.pid
            instance.port = info.port
            instance.started_at = _started_at(info)
            instance.stopped_at = None
            instance.last_error = None
            instance.updated_at = utcnow()
            return True

        age = _age_seconds(instance.updated_at)
        if age is not None and age > STARTUP_GRACE_SECONDS:
            _mark_error(instance, "The local worker did not become healthy in time.")
            return True
        return False

    if instance.status == "running":
        if alive:
            return False
        _mark_error(instance, "The local worker process is no longer running.")
        return True

    return False


def list_instances(db: Session, user: User) -> list[ComputeInstance]:
    adapter = _adapter()
    instances = instance_repo.list_by_user(db, account_owner_user_id(user))
    changed = False
    for instance in instances:
        if _refresh_instance(db, instance, adapter):
            changed = True
    if changed:
        db.commit()
    return instances


def get_instance(db: Session, user: User, instance_id: int) -> ComputeInstance:
    instance = _get_owned(db, user, instance_id)
    if _refresh_instance(db, instance, _adapter()):
        db.commit()
    return instance


def create_instance(
    db: Session, user: User, payload: CreateInstanceRequest
) -> ComputeInstance:
    instance = instance_repo.create(
        db, user_id=account_owner_user_id(user), name=payload.name
    )
    activity_service.record(
        db,
        user_id=account_owner_user_id(user),
        service="compute",
        action="created",
        resource_type="compute_instance",
        resource_id=instance.id,
        resource_name=instance.name,
    )
    db.commit()
    db.refresh(instance)
    return instance


def start_instance(db: Session, user: User, instance_id: int) -> ComputeInstance:
    instance = _get_owned(db, user, instance_id)
    adapter = _adapter()
    if _refresh_instance(db, instance, adapter):
        db.commit()

    if instance.status in ACTIVE_STATUSES:
        raise ConflictError(
            "instance_not_stopped",
            "This instance is already starting, running, or stopping.",
        )

    # Clean up any stale worker left by an earlier failed or interrupted run.
    adapter.stop(instance.id, instance.pid, timeout=2.0)

    instance.status = "starting"
    instance.last_error = None
    instance.port = None
    instance.pid = None
    instance.started_at = None
    instance.stopped_at = None
    instance.updated_at = utcnow()
    db.commit()

    try:
        info = adapter.start(instance.id, instance.name)
    except ComputeAdapterError as exc:
        _mark_error(instance, str(exc))
        activity_service.record(
            db,
            user_id=account_owner_user_id(user),
            service="compute",
            action="failed",
            resource_type="compute_instance",
            resource_id=instance.id,
            resource_name=instance.name,
        )
        db.commit()
        raise ServiceUnavailableError(
            "instance_start_failed", f"The instance could not start: {exc}"
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected compute start failure for instance %s", instance.id)
        _mark_error(instance, "An unexpected error occurred while starting the worker.")
        activity_service.record(
            db,
            user_id=account_owner_user_id(user),
            service="compute",
            action="failed",
            resource_type="compute_instance",
            resource_id=instance.id,
            resource_name=instance.name,
        )
        db.commit()
        raise ServiceUnavailableError(
            "instance_start_failed", "The instance could not start."
        ) from exc

    instance.status = "running"
    instance.pid = info.pid
    instance.port = info.port
    instance.started_at = _started_at(info)
    instance.stopped_at = None
    instance.last_error = None
    instance.updated_at = utcnow()
    activity_service.record(
        db,
        user_id=account_owner_user_id(user),
        service="compute",
        action="started",
        resource_type="compute_instance",
        resource_id=instance.id,
        resource_name=instance.name,
    )
    db.commit()
    db.refresh(instance)
    return instance


def stop_instance(db: Session, user: User, instance_id: int) -> ComputeInstance:
    instance = _get_owned(db, user, instance_id)
    adapter = _adapter()
    if _refresh_instance(db, instance, adapter):
        db.commit()

    if instance.status == "stopped":
        return instance

    instance.status = "stopping"
    instance.updated_at = utcnow()
    db.commit()

    try:
        stopped = adapter.stop(instance.id, instance.pid)
    except Exception:
        logger.exception("Unexpected compute stop failure for instance %s", instance.id)
        stopped = False

    if stopped:
        _mark_stopped(instance)
        activity_service.record(
            db,
            user_id=account_owner_user_id(user),
            service="compute",
            action="stopped",
            resource_type="compute_instance",
            resource_id=instance.id,
            resource_name=instance.name,
        )
        db.commit()
        db.refresh(instance)
        return instance

    _mark_error(instance, "The local worker did not stop within the timeout.")
    activity_service.record(
        db,
        user_id=account_owner_user_id(user),
        service="compute",
        action="failed",
        resource_type="compute_instance",
        resource_id=instance.id,
        resource_name=instance.name,
    )
    db.commit()
    raise ServiceUnavailableError(
        "instance_stop_failed",
        "The local worker did not stop. Review the logs before trying again.",
    )


def delete_instance(db: Session, user: User, instance_id: int) -> None:
    instance = _get_owned(db, user, instance_id)
    adapter = _adapter()
    if _refresh_instance(db, instance, adapter):
        db.commit()

    try:
        stopped = adapter.stop(instance.id, instance.pid, timeout=4.0)
    except Exception:
        logger.exception("Unexpected compute cleanup failure for instance %s", instance.id)
        stopped = False
    if not stopped:
        _mark_error(instance, "The local worker could not be stopped before deletion.")
        db.commit()
        raise ServiceUnavailableError(
            "instance_delete_failed",
            "The running worker could not be stopped, so the instance was not deleted.",
        )
    if instance.status != "stopped":
        _mark_stopped(instance)
        db.commit()

    try:
        adapter.remove(instance.id)
    except OSError as exc:
        logger.exception("Could not remove files for compute instance %s", instance.id)
        raise AppError(
            500,
            "instance_delete_failed",
            "The instance files could not be removed.",
        ) from exc

    activity_service.record(
        db,
        user_id=account_owner_user_id(user),
        service="compute",
        action="deleted",
        resource_type="compute_instance",
        resource_id=instance.id,
        resource_name=instance.name,
    )
    instance_repo.delete(db, instance)
    db.commit()


def read_logs(db: Session, user: User, instance_id: int) -> tuple[str, bool]:
    instance = get_instance(db, user, instance_id)
    return _adapter().read_logs(instance.id)


def stop_all_active(db: Session) -> None:
    """Best-effort cleanup of managed workers during API shutdown."""
    adapter = _adapter()
    instances = instance_repo.list_active(db)
    for instance in instances:
        try:
            info = adapter.read_worker_info(instance.id)
            pid = info.pid if info is not None else instance.pid
            if adapter.stop(instance.id, pid, timeout=3.0):
                _mark_stopped(instance)
            else:
                _mark_error(instance, "The worker did not stop during API shutdown.")
        except Exception:
            logger.exception("Could not stop compute instance %s during shutdown", instance.id)
            _mark_error(instance, "The worker could not be stopped during API shutdown.")
    if instances:
        db.commit()
