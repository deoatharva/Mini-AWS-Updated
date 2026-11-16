from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.database.session import get_db
from app.main import app


@pytest.fixture()
def session_factory(tmp_path) -> Iterator[sessionmaker]:
    """Isolated metadata database for each test; never touches data/mini_aws.db."""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'metadata.db').as_posix()}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def client(session_factory: sessionmaker) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        test_client.close()
