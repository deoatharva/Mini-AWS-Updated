from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Account(Base):
    """A local tenant. ``account_id`` is the displayable 12-digit identifier."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_accounts_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(12), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    # Deliberately not a database foreign key: users.account_id already references
    # this table and a circular FK would prevent SQLite table creation. The owner
    # relationship is maintained by the application and verified by tests.
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
