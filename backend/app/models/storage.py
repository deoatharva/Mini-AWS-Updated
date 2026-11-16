from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Bucket(Base):
    __tablename__ = "buckets"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_buckets_user_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(63), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StorageObject(Base):
    __tablename__ = "storage_objects"
    __table_args__ = (
        UniqueConstraint("bucket_id", "object_key", name="uq_storage_objects_bucket_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bucket_id: Mapped[int] = mapped_column(
        ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    object_key: Mapped[str] = mapped_column(String(200), nullable=False)
    storage_name: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    etag: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
