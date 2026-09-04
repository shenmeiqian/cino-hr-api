from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class RecruitingCreate(BaseModel):
    req_no: str
    position_id: Optional[int] = None
    dept_id: Optional[int] = None
    headcount: int = 1
    status: str = "open"
    owner_emp_id: Optional[int] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    remark: Optional[str] = None


class RecruitingUpdate(BaseModel):
    headcount: Optional[int] = None
    status: Optional[str] = None
    owner_emp_id: Optional[int] = None
    close_date: Optional[date] = None
    remark: Optional[str] = None


class RecruitingOut(ORMModel):
    id: int
    req_no: str
    position_id: Optional[int] = None
    dept_id: Optional[int] = None
    headcount: int
    status: str
    owner_emp_id: Optional[int] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
