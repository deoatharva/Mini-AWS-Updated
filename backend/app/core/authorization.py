import json
from collections import defaultdict

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.action_registry import VALID_ACTIONS, document_actions
from app.core.exceptions import ForbiddenError
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.iam import GroupMembership, GroupPolicyAttachment, IamGroup, Policy
from app.models.user import User


def is_owner(user: User) -> bool:
    return getattr(user, "user_type", "OWNER") != "IAM"


def effective_action_sources(db: Session, user: User) -> dict[str, list[dict]]:
    """Return the union of allowed actions and the group/policy sources.

    Owners are implicitly allowed every registered action within their own
    account. IAM users are deny-by-default and receive only actions explicitly
    listed in an Allow statement attached to one of their groups.
    """
    if is_owner(user):
        return {
            action: [{"type": "owner", "name": "Local account owner"}]
            for action in sorted(VALID_ACTIONS)
        }

    rows = db.execute(
        select(Policy, IamGroup.id, IamGroup.name)
        .join(GroupPolicyAttachment, GroupPolicyAttachment.policy_id == Policy.id)
        .join(IamGroup, IamGroup.id == GroupPolicyAttachment.group_id)
        .join(GroupMembership, GroupMembership.group_id == IamGroup.id)
        .where(
            GroupMembership.user_id == user.id,
            GroupMembership.account_id == user.account_id,
            IamGroup.account_id == user.account_id,
            or_(Policy.account_id.is_(None), Policy.account_id == user.account_id),
        )
    ).all()

    sources: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, int, int]] = set()
    for policy, group_id, group_name in rows:
        try:
            document = json.loads(policy.document_json)
        except json.JSONDecodeError:
            continue
        for action in document_actions(document):
            marker = (action, policy.id, group_id)
            if marker in seen:
                continue
            seen.add(marker)
            sources[action].append(
                {
                    "type": "group_policy",
                    "name": policy.name,
                    "policy_id": policy.id,
                    "policy_name": policy.name,
                    "group_id": group_id,
                    "group_name": group_name,
                }
            )
    return dict(sources)


def actions_for_user(db: Session, user: User) -> set[str]:
    return set(effective_action_sources(db, user))


def has_action(db: Session, user: User, action: str) -> bool:
    return action in actions_for_user(db, user)


def require_permission(action: str):
    """FastAPI dependency enforcing one central action for an endpoint."""
    if action not in VALID_ACTIONS:
        raise RuntimeError(f"Unknown permission action: {action}")

    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if getattr(current_user, "must_change_password", False):
            raise ForbiddenError(
                "password_change_required",
                "Change your temporary password before using the console.",
            )
        if not has_action(db, current_user, action):
            raise ForbiddenError(
                "access_denied",
                f"You do not have permission to perform {action}.",
            )
        return current_user

    return dependency


def get_ready_user(current_user: User = Depends(get_current_user)) -> User:
    """Authenticated user allowed to use normal console profile endpoints."""
    if getattr(current_user, "must_change_password", False):
        raise ForbiddenError(
            "password_change_required",
            "Change your temporary password before using the console.",
        )
    return current_user
