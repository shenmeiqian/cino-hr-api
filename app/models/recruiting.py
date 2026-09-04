"""T04 Recruiting / 入职业务闭环."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecruitingReq(Base):
    """招聘入职闭环：编制→需求→候选人→审批→入职→合同→培训→开权."""

    __tablename__ = "recruiting_reqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    req_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    position_id: Mapped[Optional[int]] = mapped_column(ForeignKey("positions.id"), nullable=True)
    dept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    # pipeline: draft|headcount_ok|open|candidate|in_approval|approved|onboarding|contract|trained|granted|closed|rejected
    status: Mapped[str] = mapped_column(String(32), default="draft")
    stage: Mapped[str] = mapped_column(String(32), default="headcount")  # current pipeline stage key
    owner_emp_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    open_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    candidate_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    candidate_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    onboarding_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
