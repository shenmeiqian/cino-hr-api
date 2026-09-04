"""T08 Permission events (grant/revoke)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PermissionEvent(Base):
    __tablename__ = "permission_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # grant / revoke
    scopes: Mapped[str] = mapped_column(Text, nullable=False)  # comma-separated or JSON list
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # leave / project_end / violation / normal
    trigger: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="done")  # pending/done/overdue
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
