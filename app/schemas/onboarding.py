from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class OnboardingCreate(BaseModel):
    employee_id: int
    plan_start: Optional[date] = None
    actual_start: Optional[date] = None
    buddy_emp_id: Optional[int] = None
    checklist_status: str = "pending"
    account_bound: bool = False
    remark: Optional[str] = None


class OnboardingUpdate(BaseModel):
    plan_start: Optional[date] = None
    actual_start: Optional[date] = None
    buddy_emp_id: Optional[int] = None
    checklist_status: Optional[str] = None
    account_bound: Optional[bool] = None
    remark: Optional[str] = None


class OnboardingOut(ORMModel):
    id: int
    employee_id: int
    plan_start: Optional[date] = None
    actual_start: Optional[date] = None
    buddy_emp_id: Optional[int] = None
    checklist_status: str
    account_bound: bool
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
