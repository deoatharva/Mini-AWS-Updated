from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.config import settings
from app.database.session import init_db


def test_init_db_creates_metadata_tables_and_data_folders(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    test_engine = create_engine(
        f"sqlite:///{(tmp_path / 'metadata.db').as_posix()}", future=True
    )

    try:
        init_db(test_engine)
        tables = set(inspect(test_engine).get_table_names())
    finally:
        test_engine.dispose()

    assert {"users", "auth_sessions"} <= tables
    for folder in (
        settings.buckets_dir,
        settings.instances_dir,
        settings.applications_dir,
        settings.databases_dir,
    ):
        assert folder.is_dir()
