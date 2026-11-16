from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ApplicationDeployment(Base):
    """Metadata for a controlled sample app served by a local worker process."""

    __tablename__ = "application_deployments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('stopped', 'starting', 'running', 'stopping', 'error')",
            name="ck_application_deployments_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    template: Mapped[str] = mapped_column(
        String(40), nullable=False, default="sample-web-app", server_default="sample-web-app"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="stopped", server_default="stopped", index=True
    )
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def local_url(self) -> str | None:
        if self.status == "running" and self.port:
            return f"http://127.0.0.1:{self.port}/"
        return None
