from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.authorization import require_permission
from app.database.session import get_db
from app.models.user import User
from app.schemas.database import (
    CreateDatabaseRequest,
    DatabaseOut,
    ExecuteSqlRequest,
    SqlResultOut,
    TableOut,
)
from app.services import database_service

router = APIRouter(prefix="/databases", tags=["databases"])


@router.get("", response_model=list[DatabaseOut])
def list_databases(
    current_user: User = Depends(require_permission("database:ListDatabases")),
    db: Session = Depends(get_db),
) -> list[DatabaseOut]:
    return database_service.list_databases(db, current_user)


@router.post("", response_model=DatabaseOut, status_code=status.HTTP_201_CREATED)
def create_database(
    payload: CreateDatabaseRequest,
    current_user: User = Depends(require_permission("database:CreateDatabase")),
    db: Session = Depends(get_db),
) -> DatabaseOut:
    return database_service.create_database(db, current_user, payload)


@router.delete("/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database(
    database_id: int,
    current_user: User = Depends(require_permission("database:DeleteDatabase")),
    db: Session = Depends(get_db),
) -> Response:
    database_service.delete_database(db, current_user, database_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{database_id}/tables", response_model=list[TableOut])
def list_tables(
    database_id: int,
    current_user: User = Depends(require_permission("database:ListTables")),
    db: Session = Depends(get_db),
) -> list[TableOut]:
    return database_service.list_tables(db, current_user, database_id)


@router.post("/{database_id}/query", response_model=SqlResultOut)
def execute_sql(
    database_id: int,
    payload: ExecuteSqlRequest,
    current_user: User = Depends(require_permission("database:ExecuteSql")),
    db: Session = Depends(get_db),
) -> SqlResultOut:
    return database_service.execute_sql(db, current_user, database_id, payload)
