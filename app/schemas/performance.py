from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PerformanceBatchCreate(BaseModel):
    year_month: str
    remark: Optional[str] = None


class PerformanceBatchOut(ORMModel):
    id: int
    year_month: str
    status: str
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None


class ScorecardMappingCreate(BaseModel):
    kpi_code: str
    kpi_name: str
    source_table: str
    formula: str
    weight: float = 0.0
    target_value: Optional[str] = None
    unit: Optional[str] = None
    remark: Optional[str] = None


class ScorecardMappingOut(ORMModel):
    id: int
    kpi_code: str
    kpi_name: str
    source_table: str
    formula: str
    weight: float
    target_value: Optional[str] = None
    unit: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None


class HrManagerScoreOut(ORMModel):
    id: int
    year_month: str
    kpi_code: str
    kpi_name: str
    raw_value: float
    score: float
    weight: float
    weighted_score: float
    detail: Optional[str] = None
    created_at: Optional[datetime] = None


class KpiRunResult(BaseModel):
    year_month: str
    batch_id: int
    scheme: str = "V2.2"
    scores: list[HrManagerScoreOut]
    total_weighted_score: float
    max_score: float = 100.0
