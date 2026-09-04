from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class AttendanceCreate(BaseModel):
    employee_id: int
    exception_date: date
    exception_type: str
    minutes: int = 0
    status: str = "open"
    remark: Optional[str] = None


class AttendanceUpdate(BaseModel):
    exception_type: Optional[str] = None
    minutes: Optional[int] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class AttendanceOut(ORMModel):
    id: int
    employee_id: int
    exception_date: date
    exception_type: str
    minutes: int
    status: str
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
