from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TrainingCreate(BaseModel):
    employee_id: int
    course_code: str
    course_name: str
    status: str = "pending"
    score: Optional[int] = None
    trained_at: Optional[date] = None
    valid_until: Optional[date] = None
    remark: Optional[str] = None


class TrainingUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[int] = None
    trained_at: Optional[date] = None
    valid_until: Optional[date] = None
    remark: Optional[str] = None


class TrainingOut(ORMModel):
    id: int
    employee_id: int
    course_code: str
    course_name: str
    status: str
    score: Optional[int] = None
    trained_at: Optional[date] = None
    valid_until: Optional[date] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
