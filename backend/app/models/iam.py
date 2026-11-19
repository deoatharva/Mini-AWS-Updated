from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class IamGroup(Base):
    __tablename__ = "iam_groups"
    __table_args__ = (
        UniqueConstraint("account_id", "name", name="uq_iam_groups_account_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    policy_attachments: Mapped[list["GroupPolicyAttachment"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_memberships_group_user"),
        Index("ix_group_memberships_account_user", "account_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("iam_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    group: Mapped["IamGroup"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_policies_version"),
        Index("ix_policies_account_name", "account_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Null account_id means an immutable, globally available built-in policy.
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    document_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_managed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class GroupPolicyAttachment(Base):
    __tablename__ = "group_policy_attachments"
    __table_args__ = (
        UniqueConstraint(
            "group_id", "policy_id", name="uq_group_policy_attachments_group_policy"
        ),
        Index("ix_group_policy_attachments_account_group", "account_id", "group_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("iam_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    group: Mapped["IamGroup"] = relationship(back_populates="policy_attachments")
    policy: Mapped["Policy"] = relationship(foreign_keys=[policy_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_account_created", "account_id", "created_at"),
        Index("ix_audit_logs_account_event", "account_id", "event_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    actor: Mapped["User | None"] = relationship(foreign_keys=[actor_user_id])
