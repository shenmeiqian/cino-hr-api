from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class RecruitingCreate(BaseModel):
    req_no: str
    position_id: Optional[int] = None
    dept_id: Optional[int] = None
    headcount: int = 1
    status: str = "draft"
    stage: str = "headcount"
    owner_emp_id: Optional[int] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    candidate_name: Optional[str] = None
    candidate_phone: Optional[str] = None
    remark: Optional[str] = None


class RecruitingUpdate(BaseModel):
    headcount: Optional[int] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    owner_emp_id: Optional[int] = None
    close_date: Optional[date] = None
    candidate_name: Optional[str] = None
    candidate_phone: Optional[str] = None
    employee_id: Optional[int] = None
    onboarding_id: Optional[int] = None
    contract_id: Optional[int] = None
    remark: Optional[str] = None


class RecruitingOut(ORMModel):
    id: int
    req_no: str
    position_id: Optional[int] = None
    dept_id: Optional[int] = None
    headcount: int
    status: str
    stage: str = "headcount"
    owner_emp_id: Optional[int] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    candidate_name: Optional[str] = None
    candidate_phone: Optional[str] = None
    employee_id: Optional[int] = None
    onboarding_id: Optional[int] = None
    contract_id: Optional[int] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    # computed
    grant_status: Optional[str] = None  # n/a|pending_train|ready|granted|failed
    timeline: Optional[list[dict[str, Any]]] = None


class PipelineAdvanceIn(BaseModel):
    action: str  # check_headcount|open_req|set_candidate|submit_approval|gen_onboarding|gen_contract|eval_grant
    candidate_name: Optional[str] = None
    candidate_phone: Optional[str] = None
    employee_id: Optional[int] = None
