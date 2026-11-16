from types import SimpleNamespace

import pytest

from app.core.exceptions import ForbiddenError
from app.core.permissions import ensure_owner, ensure_owner_id
from app.models.user import User


def test_ensure_owner_allows_matching_owner() -> None:
    current_user = User(id=7)
    resource = SimpleNamespace(user_id=7)

    ensure_owner(resource, current_user)
    ensure_owner_id(7, current_user)


def test_ensure_owner_rejects_other_local_account() -> None:
    current_user = User(id=7)
    resource = SimpleNamespace(user_id=8)

    with pytest.raises(ForbiddenError) as resource_error:
        ensure_owner(resource, current_user)

    assert resource_error.value.status_code == 403
    assert resource_error.value.code == "resource_forbidden"

    with pytest.raises(ForbiddenError):
        ensure_owner_id(8, current_user)
