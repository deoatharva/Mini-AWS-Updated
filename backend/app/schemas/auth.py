import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import BCRYPT_MAX_BYTES
from app.schemas.common import as_utc
from app.schemas.iam import GroupRefOut, USERNAME_PATTERN, validate_password_bytes

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=200)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("email")
    @classmethod
    def _clean_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not EMAIL_PATTERN.match(cleaned):
            raise ValueError("Enter a valid email address.")
        return cleaned

    @field_validator("password")
    @classmethod
    def _check_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
        return value


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)

    @field_validator("new_password")
    @classmethod
    def _check_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
        return value


class MandatoryPasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=200)
    confirm_password: str = Field(min_length=12, max_length=200)

    @field_validator("new_password", "confirm_password")
    @classmethod
    def _check_password_length(cls, value: str) -> str:
        return validate_password_bytes(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> "MandatoryPasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _clean_email(cls, value: str) -> str:
        return value.strip().lower()


class IAMLoginRequest(BaseModel):
    account_id: str = Field(pattern=r"^\d{12}$")
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(cleaned):
            raise ValueError("Enter a valid IAM username.")
        return cleaned


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: str
    name: str
    status: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _created_at_as_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class UserOut(BaseModel):
    id: int
    account_id: int
    username: str
    name: str
    display_name: str
    email: str | None = None
    user_type: str
    status: str
    console_access_enabled: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    account: AccountOut | None = None
    groups: list[GroupRefOut] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", "last_login_at")
    @classmethod
    def _dates_as_utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value is not None else None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut

    @field_validator("expires_at")
    @classmethod
    def _expires_at_as_utc(cls, value: datetime) -> datetime:
        return as_utc(value)
