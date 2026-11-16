from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compute_instance import ComputeInstance


def list_by_user(db: Session, user_id: int) -> list[ComputeInstance]:
    return list(
        db.scalars(
            select(ComputeInstance)
            .where(ComputeInstance.user_id == user_id)
            .order_by(ComputeInstance.created_at.desc(), ComputeInstance.id.desc())
        )
    )


def get_by_id(db: Session, instance_id: int) -> ComputeInstance | None:
    return db.get(ComputeInstance, instance_id)


def list_active(db: Session) -> list[ComputeInstance]:
    return list(
        db.scalars(
            select(ComputeInstance).where(
                ComputeInstance.status.in_(("starting", "running", "stopping"))
                | ((ComputeInstance.status == "error") & (ComputeInstance.pid.is_not(None)))
            )
        )
    )


def create(db: Session, *, user_id: int, name: str) -> ComputeInstance:
    instance = ComputeInstance(user_id=user_id, name=name, adapter="process", status="stopped")
    db.add(instance)
    db.flush()
    return instance


def delete(db: Session, instance: ComputeInstance) -> None:
    db.delete(instance)
