from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base
from app import models  # noqa: F401  (registers models on Base.metadata)


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(settings.database_url, future=True, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """SQLite ignores foreign keys unless they are enabled per connection."""
    module_name = type(dbapi_connection).__module__
    if "sqlite" not in module_name:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind: Engine | None = None) -> None:
    """Create data folders, upgrade legacy metadata, and seed built-in policies."""
    from app.database.legacy_schema import run_legacy_migrations
    from app.services.policy_service import seed_builtin_policies

    target = bind or engine
    settings.ensure_data_dirs()
    Base.metadata.create_all(bind=target)
    run_legacy_migrations(target)
    with Session(bind=target) as db:
        seed_builtin_policies(db)
