"""T10 Performance batches, T11 Scorecard mappings, T15 HR manager scores."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PerformanceBatch(Base):
    """T10 绩效批次."""

    __tablename__ = "performance_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year_month: Mapped[str] = mapped_column(String(7), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="open"
    )  # open/running/closed
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScorecardMapping(Base):
    """T11 KPI 条款映射."""

    __tablename__ = "scorecard_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kpi_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    kpi_name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_table: Mapped[str] = mapped_column(String(64), nullable=False)  # T01..T15
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    target_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HrManagerScore(Base):
    """T15 人事主管 KPI 得分."""

    __tablename__ = "hr_manager_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    kpi_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kpi_name: Mapped[str] = mapped_column(String(256), nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, default=0.0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    weighted_score: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
