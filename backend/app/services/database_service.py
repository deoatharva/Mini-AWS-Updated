import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.databases.sqlite_adapter import (
    DatabaseAdapterError,
    SQLExecutionError,
    SQLiteDatabaseAdapter,
)
from app.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, ValidationError
from app.core.permissions import ensure_owner
from app.models.database_resource import DatabaseResource
from app.models.user import User
from app.repositories import databases as database_repo
from app.schemas.database import (
    CreateDatabaseRequest,
    DatabaseOut,
    ExecuteSqlRequest,
    SqlResultOut,
    TableColumnOut,
    TableOut,
)
from app.services import activity_service
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


def _adapter() -> SQLiteDatabaseAdapter:
    return SQLiteDatabaseAdapter(settings.databases_dir)


def _get_owned(
    db: Session, user: User, database_id: int
) -> DatabaseResource:
    resource = database_repo.get_by_id(db, database_id)
    if resource is None:
        raise NotFoundError("database_not_found", "Database not found.")
    ensure_owner(resource, user)
    return resource


def _summary(resource: DatabaseResource) -> DatabaseOut:
    database_id = resource.id
    adapter = _adapter()
    try:
        tables = adapter.describe_tables(resource.user_id, database_id)
        status = "available"
        table_count = sum(1 for table in tables if table.kind == "table")
        last_error = None
    except DatabaseAdapterError as exc:
        logger.warning("Could not inspect database %s: %s", database_id, exc)
        status = "error"
        table_count = 0
        last_error = str(exc)
    return DatabaseOut(
        id=database_id,
        name=resource.name,
        engine=resource.engine,
        status=status,
        table_count=table_count,
        last_error=last_error,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def list_databases(db: Session, user: User) -> list[DatabaseOut]:
    return [
        _summary(resource)
        for resource in database_repo.list_by_user(db, user.id)
    ]


def create_database(
    db: Session, user: User, payload: CreateDatabaseRequest
) -> DatabaseOut:
    if database_repo.get_by_name(db, user.id, payload.name) is not None:
        raise ConflictError(
            "database_already_exists",
            "A database with that name already exists in your account.",
        )

    adapter = _adapter()
    resource: DatabaseResource | None = None
    try:
        resource = database_repo.create(db, user_id=user.id, name=payload.name)
        adapter.create_database(user.id, resource.id)
        activity_service.record(
            db,
            user_id=user.id,
            service="databases",
            action="created",
            resource_type="database",
            resource_id=resource.id,
            resource_name=resource.name,
        )
        db.commit()
        db.refresh(resource)
    except IntegrityError as exc:
        db.rollback()
        if resource is not None:
            try:
                adapter.delete_database(user.id, resource.id)
            except DatabaseAdapterError:
                pass
        raise ConflictError(
            "database_already_exists",
            "A database with that name already exists in your account.",
        ) from exc
    except (DatabaseAdapterError, OSError) as exc:
        db.rollback()
        if resource is not None:
            try:
                adapter.delete_database(user.id, resource.id)
            except DatabaseAdapterError:
                pass
        logger.exception("Could not create the local database file")
        raise AppError(
            500,
            "database_create_failed",
            "The local database file could not be created.",
        ) from exc

    return _summary(resource)


def delete_database(db: Session, user: User, database_id: int) -> None:
    resource = _get_owned(db, user, database_id)
    user_id = resource.user_id
    activity_service.record(
        db,
        user_id=user.id,
        service="databases",
        action="deleted",
        resource_type="database",
        resource_id=resource.id,
        resource_name=resource.name,
    )
    db.delete(resource)
    db.commit()
    try:
        _adapter().delete_database(user_id, database_id)
    except DatabaseAdapterError:
        logger.exception("Could not remove local database file %s", database_id)


def list_tables(db: Session, user: User, database_id: int) -> list[TableOut]:
    resource = _get_owned(db, user, database_id)
    try:
        tables = _adapter().describe_tables(resource.user_id, resource.id)
    except DatabaseAdapterError as exc:
        raise AppError(
            500,
            "database_unavailable",
            str(exc),
        ) from exc
    return [
        TableOut(
            name=table.name,
            kind=table.kind,
            columns=[
                TableColumnOut(
                    name=column.name,
                    type=column.type,
                    not_null=column.not_null,
                    default_value=column.default,
                    primary_key=column.primary_key,
                )
                for column in table.columns
            ],
        )
        for table in tables
    ]


def execute_sql(
    db: Session, user: User, database_id: int, payload: ExecuteSqlRequest
) -> SqlResultOut:
    resource = _get_owned(db, user, database_id)
    adapter = _adapter()
    try:
        result = adapter.execute_sql(resource.user_id, resource.id, payload.sql)
    except SQLExecutionError as exc:
        raise ValidationError("sql_error", str(exc)) from exc
    except DatabaseAdapterError as exc:
        raise AppError(500, "database_unavailable", str(exc)) from exc

    resource.updated_at = utcnow()
    db.commit()
    return SqlResultOut(
        columns=result.columns,
        rows=result.rows,
        rows_affected=result.rows_affected,
        duration_ms=result.duration_ms,
        truncated=result.truncated,
        statement_type=result.statement_type,
    )
