from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_session, get_current_user
from app.database.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(issued: auth_service.IssuedSession) -> TokenResponse:
    return TokenResponse(
        access_token=issued.token,
        expires_at=issued.expires_at,
        user=UserOut.model_validate(issued.user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return _token_response(auth_service.register(db, payload))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return _token_response(auth_service.login(db, email=payload.email, password=payload.password))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    user = auth_service.update_profile(db, current_user, name=payload.name)
    return UserOut.model_validate(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> Response:
    auth_service.change_password(
        db,
        current_user,
        auth_session,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> Response:
    auth_service.logout(db, auth_session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
