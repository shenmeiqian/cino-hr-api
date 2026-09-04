from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PositionClauseCreate(BaseModel):
    clause_code: str
    clause_title: str
    content: Optional[str] = None
    weight: int = 0
    sort_order: int = 0


class PositionClauseOut(ORMModel):
    id: int
    position_id: int
    clause_code: str
    clause_title: str
    content: Optional[str] = None
    weight: int
    sort_order: int


class PositionCreate(BaseModel):
    code: str
    title: str
    dept_id: Optional[int] = None
    level: Optional[str] = None
    is_universal_temp: bool = False
    jd_summary: Optional[str] = None
    status: str = "active"
    clauses: list[PositionClauseCreate] = []


class PositionUpdate(BaseModel):
    title: Optional[str] = None
    dept_id: Optional[int] = None
    level: Optional[str] = None
    is_universal_temp: Optional[bool] = None
    jd_summary: Optional[str] = None
    status: Optional[str] = None


class PositionOut(ORMModel):
    id: int
    code: str
    title: str
    dept_id: Optional[int] = None
    level: Optional[str] = None
    is_universal_temp: bool
    jd_summary: Optional[str] = None
    status: str
    clauses: list[PositionClauseOut] = []
    created_at: Optional[datetime] = None
