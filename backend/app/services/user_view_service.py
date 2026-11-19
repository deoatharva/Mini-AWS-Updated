from sqlalchemy.orm import Session

from app.core.authorization import effective_action_sources
from app.models.user import User
from app.repositories import iam as iam_repo
from app.schemas.auth import AccountOut, UserOut


def user_out(db: Session, user: User) -> UserOut:
    """Build the safe public user profile with effective permissions."""
    sources = effective_action_sources(db, user)
    groups = []
    if getattr(user, "user_type", "OWNER") == "IAM":
        groups = [
            {"id": membership.group.id, "name": membership.group.name}
            for membership in iam_repo.memberships_for_user(db, user.id)
        ]
    account = getattr(user, "account", None)
    return UserOut(
        id=user.id,
        account_id=user.account_id,
        username=user.username,
        name=user.name,
        display_name=user.name,
        email=user.email if user.user_type == "OWNER" else None,
        user_type=user.user_type,
        status=user.status,
        console_access_enabled=user.console_access_enabled,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        updated_at=user.updated_at or user.created_at,
        last_login_at=user.last_login_at,
        account=AccountOut.model_validate(account) if account is not None else None,
        groups=groups,
        permissions=sorted(sources),
    )
