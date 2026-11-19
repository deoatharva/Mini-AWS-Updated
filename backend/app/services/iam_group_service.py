from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.iam import GroupMembership, GroupPolicyAttachment, IamGroup, Policy
from app.models.user import User
from app.repositories import iam as iam_repo
from app.schemas.iam import (
    GroupCreateRequest,
    GroupDetailOut,
    GroupMemberOut,
    GroupSummaryOut,
    GroupUpdateRequest,
    PolicyIdsRequest,
    UserIdsRequest,
)
from app.services import audit_service, policy_service
from app.utils.time import utcnow


def _group_summary(db: Session, group: IamGroup) -> GroupSummaryOut:
    counts = iam_repo.group_counts(db, group.account_id).get(group.id, (0, 0))
    return GroupSummaryOut(
        id=group.id,
        name=group.name,
        description=group.description,
        user_count=counts[0],
        policy_count=counts[1],
        created_at=group.created_at,
        updated_at=group.updated_at or group.created_at,
    )


def _group_detail(db: Session, group: IamGroup) -> GroupDetailOut:
    summary = _group_summary(db, group)
    members = [
        GroupMemberOut(
            id=membership.user.id,
            username=membership.user.username,
            display_name=membership.user.name,
            status=membership.user.status,
            console_access_enabled=membership.user.console_access_enabled,
        )
        for membership in iam_repo.memberships_for_group(
            db, group.account_id, group.id
        )
    ]
    policies = [
        policy_service.serialize_policy(
            attachment.policy,
            iam_repo.policy_group_count(
                db, group.account_id, attachment.policy_id
            ),
        )
        for attachment in iam_repo.policy_attachments_for_group(
            db, group.account_id, group.id
        )
    ]
    return GroupDetailOut(**summary.model_dump(), members=members, policies=policies)


def _get_group(db: Session, actor: User, group_id: int) -> IamGroup:
    group = iam_repo.get_group(db, actor.account_id, group_id)
    if group is None:
        raise NotFoundError("iam_group_not_found", "IAM group not found.")
    return group


def _valid_policies(db: Session, actor: User, policy_ids: list[int]) -> list[Policy]:
    policies = []
    for policy_id in policy_ids:
        policy = iam_repo.get_accessible_policy(db, actor.account_id, policy_id)
        if policy is None:
            raise ValidationError(
                "policy_not_found",
                "One or more selected policies do not exist in this local account.",
            )
        policies.append(policy)
    return policies


def _reject_self_escalation(db: Session, actor: User, group: IamGroup) -> None:
    if getattr(actor, "user_type", "OWNER") != "IAM":
        return
    if iam_repo.get_membership(db, actor.account_id, group.id, actor.id) is not None:
        raise ForbiddenError(
            "self_permission_escalation",
            "IAM users cannot change the policies of a group they belong to.",
        )


def list_groups(db: Session, actor: User) -> list[GroupSummaryOut]:
    return [
        _group_summary(db, group)
        for group in iam_repo.list_groups(db, actor.account_id)
    ]


def get_group(db: Session, actor: User, group_id: int) -> GroupDetailOut:
    return _group_detail(db, _get_group(db, actor, group_id))


def create_group(
    db: Session, actor: User, payload: GroupCreateRequest
) -> GroupDetailOut:
    if iam_repo.group_name_exists(db, actor.account_id, payload.name):
        raise ConflictError(
            "group_name_exists",
            "An IAM group with that name already exists in this local account.",
        )
    policies = _valid_policies(db, actor, payload.policy_ids)
    try:
        group = IamGroup(
            account_id=actor.account_id,
            name=payload.name,
            description=payload.description,
        )
        db.add(group)
        db.flush()
        for policy in policies:
            db.add(
                GroupPolicyAttachment(
                    account_id=actor.account_id,
                    group_id=group.id,
                    policy_id=policy.id,
                )
            )
            audit_service.record(
                db,
                account_pk=actor.account_id,
                actor=actor,
                event_type="iam.policy.attached",
                target_type="group",
                target_id=group.id,
                metadata={
                    "group_name": group.name,
                    "policy_id": policy.id,
                    "policy_name": policy.name,
                    "via": "group_creation",
                },
            )
        audit_service.record(
            db,
            account_pk=actor.account_id,
            actor=actor,
            event_type="iam.group.created",
            target_type="group",
            target_id=group.id,
            metadata={"name": group.name},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "group_name_exists",
            "An IAM group with that name already exists in this local account.",
        ) from exc
    db.refresh(group)
    return _group_detail(db, group)


def update_group(
    db: Session, actor: User, group_id: int, payload: GroupUpdateRequest
) -> GroupDetailOut:
    group = _get_group(db, actor, group_id)
    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None:
        if iam_repo.group_name_exists(
            db, actor.account_id, payload.name, exclude_id=group.id
        ):
            raise ConflictError(
                "group_name_exists",
                "An IAM group with that name already exists in this local account.",
            )
        group.name = payload.name
    if "description" in fields:
        group.description = payload.description
    group.updated_at = utcnow()
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type="iam.group.updated",
        target_type="group",
        target_id=group.id,
        metadata={"name": group.name},
    )
    db.commit()
    db.refresh(group)
    return _group_detail(db, group)


def delete_group(db: Session, actor: User, group_id: int) -> None:
    group = _get_group(db, actor, group_id)
    name = group.name
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type="iam.group.deleted",
        target_type="group",
        target_id=group.id,
        metadata={"name": name},
    )
    db.delete(group)
    db.commit()


def add_users(
    db: Session, actor: User, group_id: int, payload: UserIdsRequest
) -> GroupDetailOut:
    group = _get_group(db, actor, group_id)
    if getattr(actor, "user_type", "OWNER") == "IAM" and actor.id in payload.user_ids:
        raise ForbiddenError(
            "self_permission_escalation",
            "IAM users cannot add their own identity to a group.",
        )
    users = []
    for user_id in payload.user_ids:
        user = iam_repo.get_iam_user(db, actor.account_id, user_id)
        if user is None:
            raise ValidationError(
                "iam_user_not_found",
                "One or more selected IAM users do not exist in this local account.",
            )
        if iam_repo.get_membership(db, actor.account_id, group.id, user.id) is not None:
            raise ConflictError(
                "membership_exists",
                f"{user.username} is already a member of this group.",
            )
        users.append(user)

    for user in users:
        db.add(
            GroupMembership(
                account_id=actor.account_id,
                group_id=group.id,
                user_id=user.id,
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
                "user_id": user.id,
                "username": user.username,
            },
        )
    db.commit()
    db.refresh(group)
    return _group_detail(db, group)


def remove_user(db: Session, actor: User, group_id: int, user_id: int) -> GroupDetailOut:
    group = _get_group(db, actor, group_id)
    membership = iam_repo.get_membership(db, actor.account_id, group.id, user_id)
    if membership is None:
        raise NotFoundError("membership_not_found", "Group membership not found.")
    username = membership.user.username
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type="iam.group.member_removed",
        target_type="group",
        target_id=group.id,
        metadata={"group_name": group.name, "user_id": user_id, "username": username},
    )
    db.delete(membership)
    db.commit()
    db.refresh(group)
    return _group_detail(db, group)


def attach_policies(
    db: Session, actor: User, group_id: int, payload: PolicyIdsRequest
) -> GroupDetailOut:
    group = _get_group(db, actor, group_id)
    _reject_self_escalation(db, actor, group)
    policies = _valid_policies(db, actor, payload.policy_ids)
    for policy in policies:
        if iam_repo.get_attachment(db, actor.account_id, group.id, policy.id) is not None:
            raise ConflictError(
                "policy_attachment_exists",
                f"{policy.name} is already attached to this group.",
            )
    for policy in policies:
        db.add(
            GroupPolicyAttachment(
                account_id=actor.account_id,
                group_id=group.id,
                policy_id=policy.id,
            )
        )
        audit_service.record(
            db,
            account_pk=actor.account_id,
            actor=actor,
            event_type="iam.policy.attached",
            target_type="group",
            target_id=group.id,
            metadata={
                "group_name": group.name,
                "policy_id": policy.id,
                "policy_name": policy.name,
            },
        )
    db.commit()
    db.refresh(group)
    return _group_detail(db, group)


def detach_policy(
    db: Session, actor: User, group_id: int, policy_id: int
) -> GroupDetailOut:
    group = _get_group(db, actor, group_id)
    _reject_self_escalation(db, actor, group)
    attachment = iam_repo.get_attachment(db, actor.account_id, group.id, policy_id)
    if attachment is None:
        raise NotFoundError("policy_attachment_not_found", "Policy attachment not found.")
    policy_name = attachment.policy.name
    audit_service.record(
        db,
        account_pk=actor.account_id,
        actor=actor,
        event_type="iam.policy.detached",
        target_type="group",
        target_id=group.id,
        metadata={
            "group_name": group.name,
            "policy_id": policy_id,
            "policy_name": policy_name,
        },
    )
    db.delete(attachment)
    db.commit()
    db.refresh(group)
    return _group_detail(db, group)
