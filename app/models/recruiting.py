"""T04 Recruiting requests."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecruitingReq(Base):
    __tablename__ = "recruiting_reqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    req_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    position_id: Mapped[Optional[int]] = mapped_column(ForeignKey("positions.id"), nullable=True)
    dept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(32), default="open"
    )  # open/interviewing/offer/filled/cancelled
    owner_emp_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    open_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
