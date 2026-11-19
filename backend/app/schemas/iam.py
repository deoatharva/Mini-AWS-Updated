import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import BCRYPT_MAX_BYTES
from app.schemas.common import as_utc

USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,31}$")
GROUP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{1,63}$")
POLICY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{2,79}$")


def validate_password_bytes(value: str) -> str:
    if len(value) > 200:
        raise ValueError("Password must be at most 200 characters.")
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    return value


class GroupRefOut(BaseModel):
    id: int
    name: str


class PermissionSourceOut(BaseModel):
    type: str
    name: str
    policy_id: int | None = None
    policy_name: str | None = None
    group_id: int | None = None
    group_name: str | None = None


class IAMUserSummaryOut(BaseModel):
    id: int
    account_id: str
    username: str
    display_name: str
    status: str
    console_access_enabled: bool
    must_change_password: bool
    groups: list[GroupRefOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    @field_validator("created_at", "updated_at", "last_login_at")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value is not None else None


class IAMUserDetailOut(IAMUserSummaryOut):
    effective_actions: list[str] = Field(default_factory=list)
    permission_sources: dict[str, list[PermissionSourceOut]] = Field(default_factory=dict)


class CreateIAMUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    display_name: str | None = Field(default=None, max_length=120)
    console_access_enabled: bool = True
    password: str = Field(min_length=12, max_length=200)
    confirm_password: str = Field(min_length=12, max_length=200)
    must_change_password: bool = True
    group_ids: list[int] = Field(default_factory=list, max_length=50)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Usernames must be 3-32 characters, start with a letter, and use "
                "only lowercase letters, numbers, hyphens, or underscores."
            )
        return cleaned

    @field_validator("display_name")
    @classmethod
    def _clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("password", "confirm_password")
    @classmethod
    def _password_length(cls, value: str) -> str:
        return validate_password_bytes(value)

    @field_validator("group_ids")
    @classmethod
    def _unique_group_ids(cls, value: list[int]) -> list[int]:
        if any(group_id < 1 for group_id in value):
            raise ValueError("Group IDs must be positive integers.")
        if len(set(value)) != len(value):
            raise ValueError("Select each group only once.")
        return value

    @model_validator(mode="after")
    def _passwords_match(self) -> "CreateIAMUserRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class UpdateIAMUserRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    status: Literal["active", "disabled"] | None = None
    console_access_enabled: bool | None = None

    @field_validator("display_name")
    @classmethod
    def _clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "UpdateIAMUserRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class ResetUserPasswordRequest(BaseModel):
    password: str = Field(min_length=12, max_length=200)
    confirm_password: str = Field(min_length=12, max_length=200)
    must_change_password: bool = True

    @field_validator("password", "confirm_password")
    @classmethod
    def _password_length(cls, value: str) -> str:
        return validate_password_bytes(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> "ResetUserPasswordRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=240)
    policy_ids: list[int] = Field(default_factory=list, max_length=50)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not GROUP_NAME_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Group names must be 2-64 characters and start with a letter or number."
            )
        return cleaned

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("policy_ids")
    @classmethod
    def _unique_policy_ids(cls, value: list[int]) -> list[int]:
        if any(policy_id < 1 for policy_id in value):
            raise ValueError("Policy IDs must be positive integers.")
        if len(set(value)) != len(value):
            raise ValueError("Select each policy only once.")
        return value


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=240)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not GROUP_NAME_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Group names must be 2-64 characters and start with a letter or number."
            )
        return cleaned

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "GroupUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class UserIdsRequest(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("user_ids")
    @classmethod
    def _unique_ids(cls, value: list[int]) -> list[int]:
        if any(user_id < 1 for user_id in value):
            raise ValueError("User IDs must be positive integers.")
        if len(set(value)) != len(value):
            raise ValueError("Select each user only once.")
        return value


class PolicyIdsRequest(BaseModel):
    policy_ids: list[int] = Field(min_length=1, max_length=50)

    @field_validator("policy_ids")
    @classmethod
    def _unique_ids(cls, value: list[int]) -> list[int]:
        if any(policy_id < 1 for policy_id in value):
            raise ValueError("Policy IDs must be positive integers.")
        if len(set(value)) != len(value):
            raise ValueError("Select each policy only once.")
        return value


class GroupMemberOut(BaseModel):
    id: int
    username: str
    display_name: str
    status: str
    console_access_enabled: bool


class PolicyOut(BaseModel):
    id: int
    name: str
    description: str
    version: int
    is_managed: bool
    group_count: int
    actions: list[str] = Field(default_factory=list)
    action_descriptions: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class GroupSummaryOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    user_count: int
    policy_count: int
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class GroupDetailOut(GroupSummaryOut):
    members: list[GroupMemberOut] = Field(default_factory=list)
    policies: list[PolicyOut] = Field(default_factory=list)


class PolicyCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    description: str = Field(min_length=1, max_length=400)
    actions: list[str] = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not POLICY_NAME_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Policy names must be 3-80 characters and start with a letter or number."
            )
        return cleaned

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A policy description is required.")
        return cleaned

    @field_validator("actions")
    @classmethod
    def _unique_actions(cls, value: list[str]) -> list[str]:
        cleaned = [action.strip() for action in value if action.strip()]
        if not cleaned:
            raise ValueError("Select at least one action.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Select each action only once.")
        return cleaned


class PolicyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=80)
    description: str | None = Field(default=None, min_length=1, max_length=400)
    actions: list[str] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not POLICY_NAME_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Policy names must be 3-80 characters and start with a letter or number."
            )
        return cleaned

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A policy description is required.")
        return cleaned

    @field_validator("actions")
    @classmethod
    def _unique_actions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [action.strip() for action in value if action.strip()]
        if not cleaned:
            raise ValueError("Select at least one action.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Select each action only once.")
        return cleaned

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "PolicyUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class ActionCatalogItem(BaseModel):
    action: str
    description: str
    category: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: str
    actor_user_id: int | None = None
    actor_username: str | None = None
    actor_display_name: str | None = None
    actor_type: str
    event_type: str
    target_type: str
    target_id: str | None = None
    success: bool
    metadata: dict = Field(default_factory=dict)
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class IAMOverviewOut(BaseModel):
    total_users: int
    active_users: int
    disabled_users: int
    total_groups: int
    total_policies: int
    recent_activity: list[AuditLogOut] = Field(default_factory=list)
