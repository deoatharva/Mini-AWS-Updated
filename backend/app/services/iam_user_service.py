from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import effective_action_sources
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.iam import GroupMembership
from app.models.user import User
from app.repositories import auth_sessions as session_repo
from app.repositories import iam as iam_repo
from app.repositories import users as user_repo
from app.schemas.iam import (
    CreateIAMUserRequest,
    GroupRefOut,
    IAMUserDetailOut,
    IAMUserSummaryOut,
    PermissionSourceOut,
    ResetUserPasswordRequest,
    UpdateIAMUserRequest,
)
from app.services import audit_service
from app.utils.time import utcnow


def _groups_for(db: Session, user: User) -> list[GroupRefOut]:
    return [
        GroupRefOut(id=membership.group.id, name=membership.group.name)
        for membership in iam_repo.memberships_for_user(db, user.id)
    ]


def _summary(db: Session, user: User) -> IAMUserSummaryOut:
    account = user.account
    return IAMUserSummaryOut(
        id=user.id,
        account_id=account.account_id,
        username=user.username,
        display_name=user.name,
        status=user.status,
        console_access_enabled=user.console_access_enabled,
        must_change_password=user.must_change_password,
        groups=_groups_for(db, user),
        created_at=user.created_at,
        updated_at=user.updated_at or user.created_at,
        last_login_at=user.last_login_at,
    )


def _detail(db: Session, user: User) -> IAMUserDetailOut:
    summary = _summary(db, user)
    sources = effective_action_sources(db, user)
    return IAMUserDetailOut(
        **summary.model_dump(),
        effective_actions=sorted(sources),
        permission_sources={
            action: [PermissionSourceOut.model_validate(source) for source in values]
            for action, values in sources.items()
        },
    )


def _get_target(db: Session, actor: User, user_id: int) -> User:
    target = iam_repo.get_iam_user(db, actor.account_id, user_id)
    if target is None:
        raise NotFoundError("iam_user_not_found", "IAM user not found.")
    return target


def _reject_self_management(actor: User, target: User) -> None:
    if getattr(actor, "user_type", "OWNER") == "IAM" and actor.id == target.id:
        raise ForbiddenError(
            "cannot_modify_self",
            "IAM users cannot change or delete their own identity through IAM management.",
        )


def _valid_groups(db: Session, actor: User, group_ids: list[int]):
    groups = []
    for group_id in group_ids:
        group = iam_repo.get_group(db, actor.account_id, group_id)
        if group is None:
            raise ValidationError(
                "group_not_found",
                "One or more selected groups do not exist in this local account.",
            )
        groups.append(group)
    return groups


def list_users(db: Session, actor: User) -> list[IAMUserSummaryOut]:
    return [_summary(db, user) for user in iam_repo.list_iam_users(db, actor.account_id)]


def get_user(db: Session, actor: User, user_id: int) -> IAMUserDetailOut:
    return _detail(db, _get_target(db, actor, user_id))


def create_user(
    db: Session, actor: User, payload: CreateIAMUserRequest
) -> IAMUserDetailOut:
    if user_repo.get_iam_username(db, actor.account_id, payload.username) is not None:
        raise ConflictError(
            "username_already_exists",
            "An IAM user with that username already exists in this local account.",
        )
    groups = _valid_groups(db, actor, payload.group_ids)

    try:
        target = user_repo.create(
            db,
            account_id=actor.account_id,
            username=payload.username,
            name=payload.display_name or payload.username,
            email=f"iam-{actor.account_id}-{uuid4().hex}@local.invalid",
            password_hash=hash_password(payload.password),
            user_type="IAM",
            status="active",
            console_access_enabled=payload.console_access_enabled,
            must_change_password=payload.must_change_password,
        )
        for group in groups:
            db.add(
                GroupMembership(
                    account_id=actor.account_id,
                    group_id=group.id,
                    user_id=target.id,
                )
            )
            audit_service.record(
                db,
                account_pk=actor.account_id,
                actor=actor,
                event_type="iam.group.member_added",
                target_type="group",
                target_id=group.id,
                metadata={
                    "group_name": group.name,
                    "user_id": target.id,
                    "username": target.username,
                    "via": "user_creation",
                },
            )
        audit_service.record(
            db,
            account_pk=actor.account_id,
            actor=actor,
            event_type="iam.user.created",
            target_type="identity",
            target_id=target.id,
            metadata={
                "username": target.username,
                "console_access_enabled": target.console_access_enabled,
                "must_change_password": target.must_change_password,
                "groups": [group.name for group in groups],
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "username_already_exists",
            "An IAM user with that username already exists in this local account.",
        ) from exc

    db.refresh(target)
    return _detail(db, target)


def update_user(
    db: Session, actor: User, user_id: int, payload: UpdateIAMUserRequest
) -> IAMUserDetailOut:
    target = _get_target(db, actor, user_id)
    _reject_self_management(actor, target)
    fields = payload.model_fields_set
    changes: dict = {}

    if "display_name" in fields:
        new_name = payload.display_name or target.username
        if new_name != target.name:
            changes["display_name"] = new_name
            target.name = new_name
    if "console_access_enabled" in fields and payload.console_access_enabled is not None:
        if payload.console_access_enabled != target.console_access_enabled:
            changes["console_access_enabled"] = payload.console_access_enabled
            target.console_access_enabled = payload.console_access_enabled
            if not payload.console_access_enabled:
                session_repo.delete_all_for_user(db, target.id)
    if "status" in fields and payload.status is not None and payload.status != target.status:
        changes["status"] = payload.status
        target.status = payload.status
        if payload.status == "disabled":
            session_repo.delete_all_for_user(db, target.id)

    target.updated_at = utcnow()
    if changes.get("status") == "disabled":
        event_type = "iam.user.deactivated"
    elif changes.get("status") == "active":
        event_type = "iam.user.activated"
    else:
        event_type = "iam.user.updated"
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type=event_type,
        target_type="identity",
        target_id=target.id,
        metadata={"username": target.username, "changes": changes},
    )
    db.commit()
    db.refresh(target)
    return _detail(db, target)


def reset_password(
    db: Session,
    actor: User,
    user_id: int,
    payload: ResetUserPasswordRequest,
) -> IAMUserDetailOut:
    target = _get_target(db, actor, user_id)
    _reject_self_management(actor, target)
    user_repo.update_password_hash(db, target, hash_password(payload.password))
    target.must_change_password = payload.must_change_password
    target.updated_at = utcnow()
    session_repo.delete_all_for_user(db, target.id)
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type="auth.password_reset",
        target_type="identity",
        target_id=target.id,
        metadata={
            "username": target.username,
            "must_change_password": target.must_change_password,
        },
    )
    db.commit()
    db.refresh(target)
    return _detail(db, target)


def delete_user(db: Session, actor: User, user_id: int) -> None:
    target = _get_target(db, actor, user_id)
    _reject_self_management(actor, target)
    username = target.username
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type="iam.user.deleted",
        target_type="identity",
        target_id=target.id,
        metadata={"username": username},
    )
    db.delete(target)
    db.commit()
