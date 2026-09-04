"""Dynamic nested sidebar menus."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SysMenu(Base):
    __tablename__ = "sys_menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sys_menus.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # null = group only
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    permission_code: Mapped[str] = mapped_column(String(128), nullable=False)  # required to see
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    component: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
