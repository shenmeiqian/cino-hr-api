"""T03 Positions / JDs with clauses."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    dept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_universal_temp: Mapped[bool] = mapped_column(Boolean, default=False)  # 通用临时岗 JD
    jd_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    clauses: Mapped[list["PositionClause"]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(back_populates="position")


class PositionClause(Base):
    __tablename__ = "position_clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"), nullable=False)
    clause_code: Mapped[str] = mapped_column(String(64), nullable=False)
    clause_title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    position: Mapped["Position"] = relationship(back_populates="clauses")


class PositionRole(Base):
    """岗位绑定系统角色：任职该岗位的用户可自动同步获得角色。"""
    __tablename__ = "position_roles"
    __table_args__ = (UniqueConstraint("position_id", "role_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("sys_roles.id"), nullable=False, index=True)
