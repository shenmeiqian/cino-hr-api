"""T05 Onboarding."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Onboarding(Base):
    __tablename__ = "onboardings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    plan_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    buddy_emp_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    checklist_status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending/in_progress/done
    account_bound: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
