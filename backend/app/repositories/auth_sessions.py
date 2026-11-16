from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.auth_session import AuthSession


def create(db: Session, *, user_id: int, token_hash: str, expires_at: datetime) -> AuthSession:
    session = AuthSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(session)
    db.flush()
    return session


def get_by_token_hash(db: Session, token_hash: str) -> AuthSession | None:
    return db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))


def delete_session(db: Session, session: AuthSession) -> None:
    db.delete(session)
    db.flush()


def delete_others_for_user(
    db: Session, user_id: int, keep_session_id: int
) -> None:
    """Revoke every session for a user except the one making the change."""
    db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.id != keep_session_id
        )
    )
    db.flush()


def delete_expired_for_user(db: Session, user_id: int, now: datetime) -> None:
    db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.expires_at <= now
        )
    )
    db.flush()
