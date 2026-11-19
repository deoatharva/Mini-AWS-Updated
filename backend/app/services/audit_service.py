import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.iam import AuditLog
from app.models.user import User
from app.repositories import iam as iam_repo
from app.schemas.common import as_utc

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|token|secret|credential|hash|api[_-]?key)", re.IGNORECASE
)


def _safe_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if _SENSITIVE_KEY.search(str(key)) else _safe_metadata(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_metadata(item) for item in value]
    return value


def record(
    db: Session,
    *,
    account_pk: int,
    actor: User | None,
    event_type: str,
    target_type: str,
    target_id: str | int | None = None,
    success: bool = True,
    metadata: dict | None = None,
) -> AuditLog:
    """Queue a safe audit entry in the caller's transaction.

    Metadata is recursively redacted for password/token/secret-like keys. Every
    caller is still responsible for never passing raw credential values.
    """
    entry = AuditLog(
        account_id=account_pk,
        actor_user_id=actor.id if actor is not None else None,
        event_type=event_type[:64],
        target_type=target_type[:40],
        target_id=str(target_id)[:64] if target_id is not None else None,
        success=success,
        metadata_json=json.dumps(
            _safe_metadata(metadata or {}),
            separators=(",", ":"),
            sort_keys=True,
        ),
    )
    db.add(entry)
    db.flush()
    return entry


def entry_out(entry: AuditLog, account_public_id: str) -> dict:
    try:
        metadata = json.loads(entry.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    actor = entry.actor
    return {
        "id": entry.id,
        "account_id": account_public_id,
        "actor_user_id": entry.actor_user_id,
        "actor_username": actor.username if actor is not None else None,
        "actor_display_name": actor.name if actor is not None else None,
        "actor_type": actor.user_type if actor is not None else "ANONYMOUS",
        "event_type": entry.event_type,
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "success": entry.success,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "created_at": as_utc(entry.created_at),
    }


def list_for_account(
    db: Session,
    account_pk: int,
    account_public_id: str,
    *,
    q: str | None = None,
    event_type: str | None = None,
    success: bool | None = None,
    limit: int = 100,
) -> list[dict]:
    entries = iam_repo.audit_logs(
        db,
        account_pk,
        q=q,
        event_type=event_type,
        success=success,
        limit=limit,
    )
    return [entry_out(entry, account_public_id) for entry in entries]
