from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class EmergencyCreate(BaseModel):
    approval_no: str
    employee_id: Optional[int] = None
    reason: str
    scopes: Optional[str] = None
    status: str = "pending"
    approver: Optional[str] = None


class EmergencyUpdate(BaseModel):
    status: Optional[str] = None
    approver: Optional[str] = None


class EmergencyOut(ORMModel):
    id: int
    approval_no: str
    employee_id: Optional[int] = None
    reason: str
    scopes: Optional[str] = None
    status: str
    approver: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
