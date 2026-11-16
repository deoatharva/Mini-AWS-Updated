from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_deployment import ApplicationDeployment


def list_by_user(db: Session, user_id: int) -> list[ApplicationDeployment]:
    return list(
        db.scalars(
            select(ApplicationDeployment)
            .where(ApplicationDeployment.user_id == user_id)
            .order_by(ApplicationDeployment.created_at.desc(), ApplicationDeployment.id.desc())
        )
    )


def get_by_id(db: Session, deployment_id: int) -> ApplicationDeployment | None:
    return db.get(ApplicationDeployment, deployment_id)


def list_active(db: Session) -> list[ApplicationDeployment]:
    return list(
        db.scalars(
            select(ApplicationDeployment).where(
                ApplicationDeployment.status.in_(("starting", "running", "stopping"))
                | (
                    (ApplicationDeployment.status == "error")
                    & (ApplicationDeployment.pid.is_not(None))
                )
            )
        )
    )


def create(db: Session, *, user_id: int, name: str) -> ApplicationDeployment:
    deployment = ApplicationDeployment(
        user_id=user_id,
        name=name,
        template="sample-web-app",
        status="stopped",
    )
    db.add(deployment)
    db.flush()
    return deployment


def delete(db: Session, deployment: ApplicationDeployment) -> None:
    db.delete(deployment)
