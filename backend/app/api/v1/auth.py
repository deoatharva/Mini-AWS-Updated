from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.authorization import get_ready_user
from app.database.session import get_db
from app.dependencies import get_current_session, get_current_user
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    IAMLoginRequest,
    LoginRequest,
    MandatoryPasswordChangeRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)
from app.services import auth_service, user_view_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(db: Session, issued: auth_service.IssuedSession) -> TokenResponse:
    return TokenResponse(
        access_token=issued.token,
        expires_at=issued.expires_at,
        user=user_view_service.user_out(db, issued.user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    return _token_response(db, auth_service.register(db, payload))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    issued = auth_service.login(db, email=payload.email, password=payload.password)
    return _token_response(db, issued)


@router.post("/iam/login", response_model=TokenResponse)
def iam_login(
    payload: IAMLoginRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    issued = auth_service.login_iam(
        db,
        account_id=payload.account_id,
        username=payload.username,
        password=payload.password,
    )
    return _token_response(db, issued)


@router.get("/me", response_model=UserOut)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    return user_view_service.user_out(db, current_user)


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> UserOut:
    user = auth_service.update_profile(db, current_user, name=payload.name)
    return user_view_service.user_out(db, user)


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


@router.post("/change-password", response_model=UserOut)
def complete_mandatory_password_change(
    payload: MandatoryPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> UserOut:
    user = auth_service.complete_mandatory_password_change(
        db,
        current_user,
        auth_session,
        new_password=payload.new_password,
    )
    return user_view_service.user_out(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> Response:
    auth_service.logout(db, auth_session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
