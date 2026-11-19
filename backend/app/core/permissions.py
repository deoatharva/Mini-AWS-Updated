from typing import Protocol

from app.core.exceptions import ForbiddenError
from app.models.user import User


class OwnedResource(Protocol):
    """Minimal contract for resource metadata that belongs to one local account."""

    user_id: int


def account_owner_user_id(current_user: User) -> int:
    """Return the owner user ID that all account resources are scoped to.

    Existing single-user databases have no account relationship loaded; their
    user ID remains the owner ID for backward compatibility.
    """
    account = getattr(current_user, "account", None)
    owner_id = getattr(account, "owner_user_id", None) if account is not None else None
    return owner_id or current_user.id


def ensure_owner(resource: OwnedResource, current_user: User) -> None:
    """Reject access to a resource owned by a different local account."""
    if resource.user_id != account_owner_user_id(current_user):
        raise ForbiddenError(
            "resource_forbidden",
            "You do not have access to this resource.",
        )


def ensure_owner_id(owner_id: int, current_user: User) -> None:
    """Ownership check for resources whose metadata has not been loaded."""
    if owner_id != account_owner_user_id(current_user):
        raise ForbiddenError(
            "resource_forbidden",
            "You do not have access to this resource.",
        )
