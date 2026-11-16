from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.database.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthSession:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError()
    return auth_service.resolve_session(db, credentials.credentials)


def get_current_user(auth_session: AuthSession = Depends(get_current_session)) -> User:
    return auth_session.user
