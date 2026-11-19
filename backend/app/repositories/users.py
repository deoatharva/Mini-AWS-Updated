from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def get_owner_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(
            User.email == email.strip().lower(),
            User.user_type == "OWNER",
        )
    )


def get_iam_username(db: Session, account_pk: int, username: str) -> User | None:
    return db.scalar(
        select(User).where(
            User.account_id == account_pk,
            User.user_type == "IAM",
            func.lower(User.username) == username.strip().lower(),
        )
    )


def get_owner_for_account(db: Session, account_pk: int) -> User | None:
    return db.scalar(
        select(User).where(
            User.account_id == account_pk,
            User.user_type == "OWNER",
        )
    )


def create(
    db: Session,
    *,
    account_id: int,
    username: str,
    name: str,
    email: str | None,
    password_hash: str,
    user_type: str = "OWNER",
    status: str = "active",
    console_access_enabled: bool = True,
    must_change_password: bool = False,
) -> User:
    user = User(
        account_id=account_id,
        username=username,
        name=name,
        email=email.strip().lower() if email else None,
        password_hash=password_hash,
        user_type=user_type,
        status=status,
        console_access_enabled=console_access_enabled,
        must_change_password=must_change_password,
    )
    db.add(user)
    db.flush()
    return user


def update_name(db: Session, user: User, name: str) -> User:
    user.name = name
    db.flush()
    return user


def update_password_hash(db: Session, user: User, password_hash: str) -> User:
    user.password_hash = password_hash
    db.flush()
    return user


def mark_login(db: Session, user: User, when: datetime) -> None:
    user.last_login_at = when
    db.flush()
