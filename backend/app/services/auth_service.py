from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.user import User
from app.repositories import auth_sessions as session_repo
from app.repositories import users as user_repo
from app.schemas.auth import RegisterRequest
from app.utils.time import utcnow


class IssuedSession:
    def __init__(self, user: User, token: str, expires_at: datetime) -> None:
        self.user = user
        self.token = token
        self.expires_at = expires_at


def _issue_session(db: Session, user: User) -> IssuedSession:
    now = utcnow()
    session_repo.delete_expired_for_user(db, user.id, now)
    expires_at = now + timedelta(hours=settings.session_ttl_hours)
    token = generate_session_token()
    auth_session = session_repo.create(
        db, user_id=user.id, token_hash=hash_session_token(token), expires_at=expires_at
    )
    return IssuedSession(user=user, token=token, expires_at=auth_session.expires_at)


def register(db: Session, payload: RegisterRequest) -> IssuedSession:
    if user_repo.get_by_email(db, payload.email) is not None:
        raise ConflictError(
            "email_already_registered", "An account with this email already exists."
        )
    try:
        user = user_repo.create(
            db,
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
        issued = _issue_session(db, user)
        db.commit()
    except IntegrityError as exc:
        # Another request may register the same email between the check and insert.
        db.rollback()
        raise ConflictError(
            "email_already_registered", "An account with this email already exists."
        ) from exc
    db.refresh(user)
    return issued


def login(db: Session, *, email: str, password: str) -> IssuedSession:
    user = user_repo.get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("invalid_credentials", "Email or password is incorrect.")
    issued = _issue_session(db, user)
    db.commit()
    db.refresh(user)
    return issued


def resolve_session(db: Session, token: str) -> AuthSession:
    if not token:
        raise UnauthorizedError()
    auth_session = session_repo.get_by_token_hash(db, hash_session_token(token))
    if auth_session is None:
        raise UnauthorizedError("invalid_token", "Your session is invalid. Sign in again.")
    if auth_session.expires_at <= utcnow():
        session_repo.delete_session(db, auth_session)
        db.commit()
        raise UnauthorizedError("session_expired", "Your session has expired. Sign in again.")
    return auth_session


def update_profile(db: Session, user: User, *, name: str) -> User:
    user_repo.update_name(db, user, name)
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session,
    user: User,
    auth_session: AuthSession,
    *,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        # 422 keeps the caller signed in; 401 would trigger a session reset client-side.
        raise ValidationError("invalid_current_password", "Current password is incorrect.")
    if verify_password(new_password, user.password_hash):
        raise ValidationError(
            "password_unchanged", "Choose a password different from the current one."
        )
    user_repo.update_password_hash(db, user, hash_password(new_password))
    session_repo.delete_others_for_user(db, user.id, auth_session.id)
    db.commit()


def logout(db: Session, auth_session: AuthSession) -> None:
    session_repo.delete_session(db, auth_session)
    db.commit()
