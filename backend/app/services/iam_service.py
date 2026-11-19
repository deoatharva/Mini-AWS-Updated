from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import iam as iam_repo
from app.schemas.iam import AuditLogOut, IAMOverviewOut
from app.services import audit_service


def get_overview(db: Session, user: User) -> IAMOverviewOut:
    total_users, active_users, disabled_users = iam_repo.count_iam_users(
        db, user.account_id
    )
    account_public_id = user.account.account_id
    recent = audit_service.list_for_account(
        db,
        user.account_id,
        account_public_id,
        limit=8,
    )
    return IAMOverviewOut(
        total_users=total_users,
        active_users=active_users,
        disabled_users=disabled_users,
        total_groups=iam_repo.count_groups(db, user.account_id),
        total_policies=iam_repo.count_policies(db, user.account_id),
        recent_activity=[AuditLogOut.model_validate(entry) for entry in recent],
    )
