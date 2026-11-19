import re
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    UnauthorizedError,
    ValidationError,
)
from app.core.login_throttle import login_throttle
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.user import User
from app.repositories import accounts as account_repo
from app.repositories import auth_sessions as session_repo
from app.repositories import users as user_repo
from app.schemas.auth import RegisterRequest
from app.services import audit_service
from app.utils.time import utcnow

INVALID_IAM_LOGIN = "Invalid account ID, username, or password."
INVALID_OWNER_LOGIN = "Email or password is incorrect."


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
        db,
        user_id=user.id,
        account_id=user.account_id,
        token_hash=hash_session_token(token),
        expires_at=expires_at,
    )
    return IssuedSession(user=user, token=token, expires_at=auth_session.expires_at)


def _owner_username(email: str) -> str:
    local = email.split("@", 1)[0].strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", local).strip("-_")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"owner-{cleaned}".strip("-")
    cleaned = cleaned[:32]
    if len(cleaned) < 3:
        cleaned = (cleaned + "owner")[:32]
    return cleaned


def _identity_can_sign_in(user: User) -> bool:
    account = getattr(user, "account", None)
    return (
        user.status == "active"
        and bool(user.console_access_enabled)
        and account is not None
        and account.status == "active"
    )


def _record_failed_login(
    db: Session,
    *,
    account_pk: int,
    method: str,
    target_id: str | int,
    username: str | None = None,
) -> None:
    audit_service.record(
        db,
        account_pk=account_pk,
        actor=None,
        event_type="auth.signin_failed",
        target_type="identity",
        target_id=target_id,
        success=False,
        metadata={"method": method, "username": username},
    )
    db.commit()


def register(db: Session, payload: RegisterRequest) -> IssuedSession:
    if user_repo.get_by_email(db, payload.email) is not None:
        raise ConflictError(
            "email_already_registered", "An account with this email already exists."
        )
    try:
        account = account_repo.create(
            db, name=f"{payload.name}'s local account"[:160]
        )
        user = user_repo.create(
            db,
            account_id=account.id,
            username=_owner_username(payload.email),
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            user_type="OWNER",
            status="active",
            console_access_enabled=True,
            must_change_password=False,
        )
        account.owner_user_id = user.id
        db.flush()
        audit_service.record(
            db,
            account_pk=account.id,
            actor=user,
            event_type="account.registered",
            target_type="account",
            target_id=account.account_id,
            metadata={"owner_username": user.username},
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
    key = f"owner:{email.strip().lower()}"
    if login_throttle.is_blocked(key):
        raise AppError(
            429,
            "login_throttled",
            "Too many sign-in attempts. Wait a few minutes and try again.",
        )

    user = user_repo.get_owner_by_email(db, email)
    if user is None:
        login_throttle.record_failure(key)
        raise UnauthorizedError("invalid_credentials", INVALID_OWNER_LOGIN)
    if not verify_password(password, user.password_hash) or not _identity_can_sign_in(user):
        login_throttle.record_failure(key)
        _record_failed_login(
            db,
            account_pk=user.account_id,
            method="owner",
            target_id=user.id,
            username=user.username,
        )
        raise UnauthorizedError("invalid_credentials", INVALID_OWNER_LOGIN)

    login_throttle.clear(key)
    now = utcnow()
    user.last_login_at = now
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="auth.signin_succeeded",
        target_type="identity",
        target_id=user.id,
        metadata={"method": "owner"},
    )
    issued = _issue_session(db, user)
    db.commit()
    db.refresh(user)
    return issued


def login_iam(
    db: Session, *, account_id: str, username: str, password: str
) -> IssuedSession:
    key = f"iam:{account_id}:{username.strip().lower()}"
    if login_throttle.is_blocked(key):
        raise AppError(
            429,
            "login_throttled",
            "Too many sign-in attempts. Wait a few minutes and try again.",
        )

    account = account_repo.get_by_public_id(db, account_id)
    if account is None:
        login_throttle.record_failure(key)
        raise UnauthorizedError("invalid_credentials", INVALID_IAM_LOGIN)

    user = user_repo.get_iam_username(db, account.id, username)
    if user is None:
        login_throttle.record_failure(key)
        _record_failed_login(
            db,
            account_pk=account.id,
            method="iam",
            target_id=username.strip().lower(),
            username=username.strip().lower(),
        )
        raise UnauthorizedError("invalid_credentials", INVALID_IAM_LOGIN)

    if not verify_password(password, user.password_hash) or not _identity_can_sign_in(user):
        login_throttle.record_failure(key)
        _record_failed_login(
            db,
            account_pk=account.id,
            method="iam",
            target_id=user.id,
            username=user.username,
        )
        raise UnauthorizedError("invalid_credentials", INVALID_IAM_LOGIN)

    login_throttle.clear(key)
    now = utcnow()
    user.last_login_at = now
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="auth.signin_succeeded",
        target_type="identity",
        target_id=user.id,
        metadata={"method": "iam"},
    )
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
    user.must_change_password = False
    session_repo.delete_others_for_user(db, user.id, auth_session.id)
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="auth.password_changed",
        target_type="identity",
        target_id=user.id,
        metadata={"method": "current_password"},
    )
    db.commit()


def complete_mandatory_password_change(
    db: Session, user: User, auth_session: AuthSession, *, new_password: str
) -> User:
    if not user.must_change_password:
        raise ValidationError(
            "password_change_not_required",
            "This account is not required to change its password.",
        )
    if verify_password(new_password, user.password_hash):
        raise ValidationError(
            "password_unchanged", "Choose a password different from the temporary password."
        )
    user_repo.update_password_hash(db, user, hash_password(new_password))
    user.must_change_password = False
    session_repo.delete_others_for_user(db, user.id, auth_session.id)
    audit_service.record(
        db,
        account_pk=user.account_id,
        actor=user,
        event_type="auth.password_changed",
        target_type="identity",
        target_id=user.id,
        metadata={"method": "first_login"},
    )
    db.commit()
    db.refresh(user)
    return user


def logout(db: Session, auth_session: AuthSession) -> None:
    session_repo.delete_session(db, auth_session)
    db.commit()
