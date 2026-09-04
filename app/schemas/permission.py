from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PermissionGrantIn(BaseModel):
    employee_id: int
    scopes: list[str] = Field(..., min_length=1, description="权限范围，如 wipe/outbound/read")
    reason: Optional[str] = None
    operator: Optional[str] = None


class PermissionRevokeIn(BaseModel):
    employee_id: int
    scopes: list[str] = Field(..., min_length=1)
    reason: Optional[str] = None
    trigger: Optional[str] = Field(
        None, description="leave / project_end / violation / normal"
    )
    operator: Optional[str] = None


class PermissionEventOut(ORMModel):
    id: int
    employee_id: int
    event_type: str
    scopes: str
    reason: Optional[str] = None
    trigger: Optional[str] = None
    status: str
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    operator: Optional[str] = None
    created_at: Optional[datetime] = None
