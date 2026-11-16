from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create(db: Session, *, name: str, email: str, password_hash: str) -> User:
    user = User(name=name, email=email.strip().lower(), password_hash=password_hash)
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
