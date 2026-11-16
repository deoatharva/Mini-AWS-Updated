from typing import Protocol

from app.core.exceptions import ForbiddenError
from app.models.user import User


class OwnedResource(Protocol):
    """Minimal contract for resource metadata that belongs to one local user."""

    user_id: int


def ensure_owner(resource: OwnedResource, current_user: User) -> None:
    """Reject access to a resource owned by a different local account."""
    if resource.user_id != current_user.id:
        raise ForbiddenError(
            "resource_forbidden",
            "You do not have access to this resource.",
        )


def ensure_owner_id(owner_id: int, current_user: User) -> None:
    """Ownership check for resources whose metadata has not been loaded."""
    if owner_id != current_user.id:
        raise ForbiddenError(
            "resource_forbidden",
            "You do not have access to this resource.",
        )
