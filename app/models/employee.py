"""T01 Employees + Departments."""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.position import Position


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class Employee(Base):
    """T01 员工主数据."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    dept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    position_id: Mapped[Optional[int]] = mapped_column(ForeignKey("positions.id"), nullable=True)
    # 综合系统3.0账号绑定
    system_account_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    # 本地 RBAC 用户双向关联
    sys_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active/leave/resigned
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    leave_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_media_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_critical_role: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    department: Mapped[Optional["Department"]] = relationship(back_populates="employees")
    position: Mapped[Optional["Position"]] = relationship(back_populates="employees")
