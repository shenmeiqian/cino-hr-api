from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class HeadcountCreate(BaseModel):
    year_month: str
    dept_id: Optional[int] = None
    position_id: Optional[int] = None
    planned_count: int = 0
    actual_count: int = 0
    vacancy: int = 0
    status: str = "draft"
    remark: Optional[str] = None


class HeadcountUpdate(BaseModel):
    planned_count: Optional[int] = None
    actual_count: Optional[int] = None
    vacancy: Optional[int] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class HeadcountOut(ORMModel):
    id: int
    year_month: str
    dept_id: Optional[int] = None
    position_id: Optional[int] = None
    planned_count: int
    actual_count: int
    vacancy: int
    status: str
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
