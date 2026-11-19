import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account


def _new_public_account_id(db: Session) -> str:
    for _ in range(100):
        candidate = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
        if get_by_public_id(db, candidate) is None:
            return candidate
    raise RuntimeError("Could not allocate a unique local account ID.")


def get_by_id(db: Session, account_pk: int) -> Account | None:
    return db.get(Account, account_pk)


def get_by_public_id(db: Session, account_id: str) -> Account | None:
    return db.scalar(select(Account).where(Account.account_id == account_id))


def create(db: Session, *, name: str) -> Account:
    account = Account(account_id=_new_public_account_id(db), name=name, status="active")
    db.add(account)
    db.flush()
    return account
