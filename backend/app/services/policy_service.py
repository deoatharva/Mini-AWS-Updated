import json

from sqlalchemy.orm import Session

from app.core.action_registry import (
    ACTION_DESCRIPTIONS,
    POLICY_DEFINITIONS,
    VALID_ACTIONS,
    document_actions,
    policy_document,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.iam import Policy
from app.models.user import User
from app.repositories import iam as iam_repo
from app.schemas.iam import (
    PolicyCreateRequest,
    PolicyOut,
    PolicyUpdateRequest,
)
from app.services import audit_service
from app.utils.time import utcnow


def seed_builtin_policies(db: Session) -> None:
    """Create or update immutable built-in policies from the central registry."""
    from sqlalchemy import select

    changed = False
    for definition in POLICY_DEFINITIONS.values():
        document = json.dumps(
            policy_document(definition.actions),
            separators=(",", ":"),
            sort_keys=True,
        )
        policy = db.scalar(
            select(Policy).where(
                Policy.account_id.is_(None),
                Policy.name == definition.name,
            )
        )
        if policy is None:
            db.add(
                Policy(
                    account_id=None,
                    name=definition.name,
                    description=definition.description,
                    version=definition.version,
                    document_json=document,
                    is_managed=True,
                )
            )
            changed = True
        else:
            if (
                policy.description != definition.description
                or policy.version != definition.version
                or policy.document_json != document
                or not policy.is_managed
            ):
                policy.description = definition.description
                policy.version = definition.version
                policy.document_json = document
                policy.is_managed = True
                policy.updated_at = utcnow()
                changed = True
    if changed:
        db.commit()


def serialize_policy(policy: Policy, group_count: int) -> PolicyOut:
    try:
        document = json.loads(policy.document_json)
    except json.JSONDecodeError:
        document = {}
    actions = sorted(document_actions(document))
    return PolicyOut(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        is_managed=policy.is_managed,
        group_count=group_count,
        actions=actions,
        action_descriptions={
            action: ACTION_DESCRIPTIONS.get(action, action) for action in actions
        },
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def list_policies(db: Session, user: User) -> list[PolicyOut]:
    usage = iam_repo.policy_usage(db, user.account_id)
    return [
        serialize_policy(policy, usage.get(policy.id, 0))
        for policy in iam_repo.list_policies(db, user.account_id)
    ]


def get_policy(db: Session, user: User, policy_id: int) -> PolicyOut:
    policy = iam_repo.get_accessible_policy(db, user.account_id, policy_id)
    if policy is None:
        raise NotFoundError("policy_not_found", "Policy not found.")
    return serialize_policy(
        policy, iam_repo.policy_group_count(db, user.account_id, policy.id)
    )


def _validated_action_set(actions: list[str]) -> set[str]:
    cleaned = {action.strip() for action in actions if action.strip()}
    if not cleaned:
        raise ValidationError(
            "policy_actions_required", "Select at least one allowed action."
        )
    invalid = cleaned - VALID_ACTIONS
    if invalid:
        raise ValidationError(
            "unknown_policy_action",
            f"Unknown action(s): {', '.join(sorted(invalid))}.",
        )
    return cleaned


def create_policy(
    db: Session, user: User, payload: PolicyCreateRequest
) -> PolicyOut:
    if iam_repo.policy_name_exists(db, user.account_id, payload.name):
        raise ConflictError(
            "policy_name_exists",
            "A built-in or custom policy with that name already exists.",
        )
    actions = _validated_action_set(payload.actions)
    policy = Policy(
        account_id=user.account_id,
        name=payload.name,
        description=payload.description,
        version=1,
        document_json=json.dumps(
            policy_document(actions), separators=(",", ":"), sort_keys=True
        ),
        is_managed=False,
    )
    db.add(policy)
    db.flush()
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="iam.policy.created",
        target_type="policy",
        target_id=policy.id,
        metadata={"name": policy.name, "actions": sorted(actions)},
    )
    db.commit()
    db.refresh(policy)
    return serialize_policy(policy, 0)


def update_policy(
    db: Session, user: User, policy_id: int, payload: PolicyUpdateRequest
) -> PolicyOut:
    policy = iam_repo.get_accessible_policy(db, user.account_id, policy_id)
    if policy is None:
        raise NotFoundError("policy_not_found", "Policy not found.")
    if policy.is_managed:
        raise ConflictError(
            "managed_policy_immutable",
            "Built-in policies are immutable. Create a custom policy instead.",
        )
    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None:
        if iam_repo.policy_name_exists(
            db, user.account_id, payload.name, exclude_id=policy.id
        ):
            raise ConflictError(
                "policy_name_exists",
                "A built-in or custom policy with that name already exists.",
            )
        policy.name = payload.name
    if "description" in fields and payload.description is not None:
        policy.description = payload.description
    if "actions" in fields and payload.actions is not None:
        actions = _validated_action_set(payload.actions)
        policy.document_json = json.dumps(
            policy_document(actions), separators=(",", ":"), sort_keys=True
        )
    policy.version += 1
    policy.updated_at = utcnow()
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="iam.policy.updated",
        target_type="policy",
        target_id=policy.id,
        metadata={"name": policy.name, "version": policy.version},
    )
    db.commit()
    db.refresh(policy)
    return serialize_policy(
        policy, iam_repo.policy_group_count(db, user.account_id, policy.id)
    )


def delete_policy(db: Session, user: User, policy_id: int) -> None:
    policy = iam_repo.get_accessible_policy(db, user.account_id, policy_id)
    if policy is None:
        raise NotFoundError("policy_not_found", "Policy not found.")
    if policy.is_managed:
        raise ConflictError(
            "managed_policy_immutable",
            "Built-in policies cannot be deleted.",
        )
    group_count = iam_repo.policy_group_count(db, user.account_id, policy.id)
    if group_count:
        raise ConflictError(
            "policy_in_use",
            f"Detach this policy from {group_count} group(s) before deleting it.",
        )
    name = policy.name
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="iam.policy.deleted",
        target_type="policy",
        target_id=policy.id,
        metadata={"name": name},
    )
    db.delete(policy)
    db.commit()
