from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.iam import (
    AuditLog,
    GroupMembership,
    GroupPolicyAttachment,
    IamGroup,
    Policy,
)
from app.models.user import User


def list_iam_users(db: Session, account_pk: int) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.account_id == account_pk, User.user_type == "IAM")
            .order_by(func.lower(User.username))
        )
    )


def get_iam_user(db: Session, account_pk: int, user_id: int) -> User | None:
    return db.scalar(
        select(User).where(
            User.id == user_id,
            User.account_id == account_pk,
            User.user_type == "IAM",
        )
    )


def memberships_for_user(db: Session, user_id: int) -> list[GroupMembership]:
    return list(
        db.scalars(
            select(GroupMembership)
            .options(joinedload(GroupMembership.group))
            .where(GroupMembership.user_id == user_id)
            .order_by(func.lower(IamGroup.name))
            .join(IamGroup, IamGroup.id == GroupMembership.group_id)
        )
    )


def memberships_for_group(db: Session, account_pk: int, group_id: int) -> list[GroupMembership]:
    return list(
        db.scalars(
            select(GroupMembership)
            .options(joinedload(GroupMembership.user))
            .where(
                GroupMembership.account_id == account_pk,
                GroupMembership.group_id == group_id,
            )
            .join(User, User.id == GroupMembership.user_id)
            .order_by(func.lower(User.username))
        )
    )


def get_membership(
    db: Session, account_pk: int, group_id: int, user_id: int
) -> GroupMembership | None:
    return db.scalar(
        select(GroupMembership).where(
            GroupMembership.account_id == account_pk,
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )


def list_groups(db: Session, account_pk: int) -> list[IamGroup]:
    return list(
        db.scalars(
            select(IamGroup)
            .where(IamGroup.account_id == account_pk)
            .order_by(func.lower(IamGroup.name))
        )
    )


def get_group(db: Session, account_pk: int, group_id: int) -> IamGroup | None:
    return db.scalar(
        select(IamGroup).where(
            IamGroup.id == group_id,
            IamGroup.account_id == account_pk,
        )
    )


def group_name_exists(
    db: Session, account_pk: int, name: str, *, exclude_id: int | None = None
) -> bool:
    statement = select(IamGroup.id).where(
        IamGroup.account_id == account_pk,
        func.lower(IamGroup.name) == name.strip().lower(),
    )
    if exclude_id is not None:
        statement = statement.where(IamGroup.id != exclude_id)
    return db.scalar(statement) is not None


def group_counts(db: Session, account_pk: int) -> dict[int, tuple[int, int]]:
    members = dict(
        db.execute(
            select(GroupMembership.group_id, func.count(GroupMembership.id))
            .where(GroupMembership.account_id == account_pk)
            .group_by(GroupMembership.group_id)
        ).all()
    )
    policies = dict(
        db.execute(
            select(GroupPolicyAttachment.group_id, func.count(GroupPolicyAttachment.id))
            .where(GroupPolicyAttachment.account_id == account_pk)
            .group_by(GroupPolicyAttachment.group_id)
        ).all()
    )
    return {
        group_id: (members.get(group_id, 0), policies.get(group_id, 0))
        for group_id in set(members) | set(policies)
    }


def policy_attachments_for_group(
    db: Session, account_pk: int, group_id: int
) -> list[GroupPolicyAttachment]:
    return list(
        db.scalars(
            select(GroupPolicyAttachment)
            .options(joinedload(GroupPolicyAttachment.policy))
            .where(
                GroupPolicyAttachment.account_id == account_pk,
                GroupPolicyAttachment.group_id == group_id,
            )
            .join(Policy, Policy.id == GroupPolicyAttachment.policy_id)
            .order_by(func.lower(Policy.name))
        )
    )


def get_attachment(
    db: Session, account_pk: int, group_id: int, policy_id: int
) -> GroupPolicyAttachment | None:
    return db.scalar(
        select(GroupPolicyAttachment).where(
            GroupPolicyAttachment.account_id == account_pk,
            GroupPolicyAttachment.group_id == group_id,
            GroupPolicyAttachment.policy_id == policy_id,
        )
    )


def list_policies(db: Session, account_pk: int) -> list[Policy]:
    return list(
        db.scalars(
            select(Policy)
            .where(or_(Policy.account_id.is_(None), Policy.account_id == account_pk))
            .order_by(Policy.is_managed.desc(), func.lower(Policy.name))
        )
    )


def get_accessible_policy(db: Session, account_pk: int, policy_id: int) -> Policy | None:
    return db.scalar(
        select(Policy).where(
            Policy.id == policy_id,
            or_(Policy.account_id.is_(None), Policy.account_id == account_pk),
        )
    )


def policy_name_exists(
    db: Session, account_pk: int, name: str, *, exclude_id: int | None = None
) -> bool:
    statement = select(Policy.id).where(
        func.lower(Policy.name) == name.strip().lower(),
        or_(Policy.account_id.is_(None), Policy.account_id == account_pk),
    )
    if exclude_id is not None:
        statement = statement.where(Policy.id != exclude_id)
    return db.scalar(statement) is not None


def policy_group_count(db: Session, account_pk: int, policy_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(GroupPolicyAttachment.id)).where(
                GroupPolicyAttachment.account_id == account_pk,
                GroupPolicyAttachment.policy_id == policy_id,
            )
        )
        or 0
    )


def policy_usage(db: Session, account_pk: int) -> dict[int, int]:
    return dict(
        db.execute(
            select(
                GroupPolicyAttachment.policy_id,
                func.count(GroupPolicyAttachment.id),
            )
            .where(GroupPolicyAttachment.account_id == account_pk)
            .group_by(GroupPolicyAttachment.policy_id)
        ).all()
    )


def audit_logs(
    db: Session,
    account_pk: int,
    *,
    q: str | None,
    event_type: str | None,
    success: bool | None,
    limit: int,
) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(AuditLog.account_id == account_pk)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    if event_type:
        statement = statement.where(AuditLog.event_type == event_type)
    if success is not None:
        statement = statement.where(AuditLog.success == success)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.outerjoin(User, User.id == AuditLog.actor_user_id).where(
            or_(
                AuditLog.event_type.ilike(pattern),
                AuditLog.target_type.ilike(pattern),
                AuditLog.target_id.ilike(pattern),
                AuditLog.metadata_json.ilike(pattern),
                User.username.ilike(pattern),
                User.name.ilike(pattern),
            )
        )
    return list(db.scalars(statement))


def count_iam_users(db: Session, account_pk: int) -> tuple[int, int, int]:
    total = int(
        db.scalar(
            select(func.count(User.id)).where(
                User.account_id == account_pk, User.user_type == "IAM"
            )
        )
        or 0
    )
    active = int(
        db.scalar(
            select(func.count(User.id)).where(
                User.account_id == account_pk,
                User.user_type == "IAM",
                User.status == "active",
            )
        )
        or 0
    )
    disabled = total - active
    return total, active, disabled


def count_groups(db: Session, account_pk: int) -> int:
    return int(
        db.scalar(
            select(func.count(IamGroup.id)).where(IamGroup.account_id == account_pk)
        )
        or 0
    )


def count_policies(db: Session, account_pk: int) -> int:
    return int(
        db.scalar(
            select(func.count(Policy.id)).where(
                or_(Policy.account_id.is_(None), Policy.account_id == account_pk)
            )
        )
        or 0
    )
