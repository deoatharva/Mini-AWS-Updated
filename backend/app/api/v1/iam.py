from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.action_registry import action_catalog
from app.core.authorization import require_permission
from app.database.session import get_db
from app.models.user import User
from app.schemas.iam import (
    ActionCatalogItem,
    AuditLogOut,
    CreateIAMUserRequest,
    GroupCreateRequest,
    GroupDetailOut,
    GroupSummaryOut,
    GroupUpdateRequest,
    IAMOverviewOut,
    IAMUserDetailOut,
    IAMUserSummaryOut,
    PolicyCreateRequest,
    PolicyIdsRequest,
    PolicyOut,
    PolicyUpdateRequest,
    ResetUserPasswordRequest,
    UpdateIAMUserRequest,
    UserIdsRequest,
)
from app.services import (
    audit_service,
    iam_group_service,
    iam_service,
    iam_user_service,
    policy_service,
)

router = APIRouter(prefix="/iam", tags=["iam"])


@router.get("/overview", response_model=IAMOverviewOut)
def overview(
    current_user: User = Depends(require_permission("iam:ReadOverview")),
    db: Session = Depends(get_db),
) -> IAMOverviewOut:
    return iam_service.get_overview(db, current_user)


@router.get("/actions", response_model=list[ActionCatalogItem])
def actions(
    current_user: User = Depends(require_permission("iam:ListPolicies")),
) -> list[ActionCatalogItem]:
    return [ActionCatalogItem.model_validate(item) for item in action_catalog()]


@router.get("/users", response_model=list[IAMUserSummaryOut])
def list_users(
    current_user: User = Depends(require_permission("iam:ListUsers")),
    db: Session = Depends(get_db),
) -> list[IAMUserSummaryOut]:
    return iam_user_service.list_users(db, current_user)


@router.post(
    "/users", response_model=IAMUserDetailOut, status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: CreateIAMUserRequest,
    current_user: User = Depends(require_permission("iam:CreateUser")),
    db: Session = Depends(get_db),
) -> IAMUserDetailOut:
    return iam_user_service.create_user(db, current_user, payload)


@router.get("/users/{user_id}", response_model=IAMUserDetailOut)
def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("iam:GetUser")),
    db: Session = Depends(get_db),
) -> IAMUserDetailOut:
    return iam_user_service.get_user(db, current_user, user_id)


@router.patch("/users/{user_id}", response_model=IAMUserDetailOut)
def update_user(
    user_id: int,
    payload: UpdateIAMUserRequest,
    current_user: User = Depends(require_permission("iam:UpdateUser")),
    db: Session = Depends(get_db),
) -> IAMUserDetailOut:
    return iam_user_service.update_user(db, current_user, user_id, payload)


@router.post("/users/{user_id}/reset-password", response_model=IAMUserDetailOut)
def reset_password(
    user_id: int,
    payload: ResetUserPasswordRequest,
    current_user: User = Depends(require_permission("iam:ResetUserPassword")),
    db: Session = Depends(get_db),
) -> IAMUserDetailOut:
    return iam_user_service.reset_password(db, current_user, user_id, payload)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("iam:DeleteUser")),
    db: Session = Depends(get_db),
) -> Response:
    iam_user_service.delete_user(db, current_user, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/groups", response_model=list[GroupSummaryOut])
def list_groups(
    current_user: User = Depends(require_permission("iam:ListGroups")),
    db: Session = Depends(get_db),
) -> list[GroupSummaryOut]:
    return iam_group_service.list_groups(db, current_user)


@router.post(
    "/groups", response_model=GroupDetailOut, status_code=status.HTTP_201_CREATED
)
def create_group(
    payload: GroupCreateRequest,
    current_user: User = Depends(require_permission("iam:CreateGroup")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.create_group(db, current_user, payload)


@router.get("/groups/{group_id}", response_model=GroupDetailOut)
def get_group(
    group_id: int,
    current_user: User = Depends(require_permission("iam:GetGroup")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.get_group(db, current_user, group_id)


@router.patch("/groups/{group_id}", response_model=GroupDetailOut)
def update_group(
    group_id: int,
    payload: GroupUpdateRequest,
    current_user: User = Depends(require_permission("iam:UpdateGroup")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.update_group(db, current_user, group_id, payload)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    current_user: User = Depends(require_permission("iam:DeleteGroup")),
    db: Session = Depends(get_db),
) -> Response:
    iam_group_service.delete_group(db, current_user, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/groups/{group_id}/users", response_model=GroupDetailOut)
def add_group_users(
    group_id: int,
    payload: UserIdsRequest,
    current_user: User = Depends(require_permission("iam:AddUserToGroup")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.add_users(db, current_user, group_id, payload)


@router.delete("/groups/{group_id}/users/{user_id}", response_model=GroupDetailOut)
def remove_group_user(
    group_id: int,
    user_id: int,
    current_user: User = Depends(require_permission("iam:RemoveUserFromGroup")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.remove_user(db, current_user, group_id, user_id)


@router.post("/groups/{group_id}/policies", response_model=GroupDetailOut)
def attach_group_policies(
    group_id: int,
    payload: PolicyIdsRequest,
    current_user: User = Depends(require_permission("iam:AttachGroupPolicy")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.attach_policies(db, current_user, group_id, payload)


@router.delete(
    "/groups/{group_id}/policies/{policy_id}", response_model=GroupDetailOut
)
def detach_group_policy(
    group_id: int,
    policy_id: int,
    current_user: User = Depends(require_permission("iam:DetachGroupPolicy")),
    db: Session = Depends(get_db),
) -> GroupDetailOut:
    return iam_group_service.detach_policy(db, current_user, group_id, policy_id)


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(
    current_user: User = Depends(require_permission("iam:ListPolicies")),
    db: Session = Depends(get_db),
) -> list[PolicyOut]:
    return policy_service.list_policies(db, current_user)


@router.post(
    "/policies", response_model=PolicyOut, status_code=status.HTTP_201_CREATED
)
def create_policy(
    payload: PolicyCreateRequest,
    current_user: User = Depends(require_permission("iam:CreatePolicy")),
    db: Session = Depends(get_db),
) -> PolicyOut:
    return policy_service.create_policy(db, current_user, payload)


@router.get("/policies/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: int,
    current_user: User = Depends(require_permission("iam:GetPolicy")),
    db: Session = Depends(get_db),
) -> PolicyOut:
    return policy_service.get_policy(db, current_user, policy_id)


@router.patch("/policies/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: int,
    payload: PolicyUpdateRequest,
    current_user: User = Depends(require_permission("iam:UpdatePolicy")),
    db: Session = Depends(get_db),
) -> PolicyOut:
    return policy_service.update_policy(db, current_user, policy_id, payload)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    current_user: User = Depends(require_permission("iam:DeletePolicy")),
    db: Session = Depends(get_db),
) -> Response:
    policy_service.delete_policy(db, current_user, policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    q: str | None = Query(default=None, max_length=120),
    event_type: str | None = Query(default=None, max_length=64),
    success: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_permission("iam:ListAuditLogs")),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    entries = audit_service.list_for_account(
        db,
        current_user.account_id,
        current_user.account.account_id,
        q=q,
        event_type=event_type,
        success=success,
        limit=limit,
    )
    return [AuditLogOut.model_validate(entry) for entry in entries]
