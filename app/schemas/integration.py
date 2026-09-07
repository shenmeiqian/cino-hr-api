"""综合系统 3.0 对接请求/响应模型。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class Sys3UserIn(BaseModel):
    id: str = Field(..., description="综合系统 3.0 用户 ID，写入 Employee.system_account_id")
    username: str = Field(..., description="登录名，用于 upsert 本地 SysUser")
    display_name: str
    dept_code: Optional[str] = Field(None, description="部门编码，若员工已存在则尝试对齐部门")
    status: str = Field("active", description="active / frozen / disabled / leave")


class SyncUsersIn(BaseModel):
    users: list[Sys3UserIn] = Field(..., min_length=1, description="3.0 用户列表")


class SyncUserItemOut(BaseModel):
    id: str
    username: str
    action: str
    sys_user_id: int
    employee_id: Optional[int] = None
    system_account_id: Optional[str] = None
    linked: bool = False
    message: Optional[str] = None


class SyncUsersOut(BaseModel):
    ok: bool
    sync_log_id: int
    created: int
    updated: int
    linked: int
    items: list[SyncUserItemOut]


class LastSyncSlice(BaseModel):
    sync_type: str
    status: Optional[str] = None
    finished_at: Optional[datetime] = None
    count_in: int = 0
    count_created: int = 0
    count_updated: int = 0
    count_linked: int = 0
    message: Optional[str] = None


class IntegrationConfigOut(ORMModel):
    id: int
    name: str
    base_url: str
    auth_mode: str
    credential_hint: Optional[str] = None
    status: str
    remark: Optional[str] = None
    updated_at: Optional[datetime] = None


class SyncStatusOut(BaseModel):
    config: Optional[IntegrationConfigOut] = None
    last_syncs: list[LastSyncSlice]
    counts: dict[str, int]


class ValidateTrainingIn(BaseModel):
    employee_id: Optional[int] = Field(None, description="本系统员工 ID")
    system_account_id: Optional[str] = Field(None, description="综合系统 3.0 账号 ID")
    scopes: list[str] = Field(..., min_length=1, description="拟授予的权限范围，如 wipe/outbound")

    @model_validator(mode="after")
    def _need_identity(self):
        if self.employee_id is None and not (self.system_account_id or "").strip():
            raise ValueError("须提供 employee_id 或 system_account_id")
        return self


class ValidateTrainingOut(BaseModel):
    ok: bool
    gate_applied: bool
    employee_id: int
    emp_no: Optional[str] = None
    name: Optional[str] = None
    system_account_id: Optional[str] = None
    is_media_contact: bool
    scopes: list[str]
    required_courses: list[str]
    missing_courses: list[str]
    detail: str


class PendingRevokeOut(BaseModel):
    employee_id: int
    emp_no: str
    name: str
    system_account_id: Optional[str] = None
    status: str
    is_critical_role: bool
    reason: str
    due_at: Optional[datetime] = None
    pending_event_id: Optional[int] = None
    scopes: Optional[str] = None


class PermissionCallbackIn(BaseModel):
    employee_id: Optional[int] = None
    system_account_id: Optional[str] = None
    event_type: str = Field(..., description="grant 或 revoke")
    scopes: list[str] = Field(..., min_length=1)
    status: str = Field("done", description="3.0 已执行结果：done / failed")
    trigger: Optional[str] = Field(None, description="leave / project_end / violation / normal")
    operator: Optional[str] = Field(None, description="3.0 侧操作者标识")
    reason: Optional[str] = None
    external_ref: Optional[str] = Field(None, description="3.0 侧单据号（写入 reason 备注）")

    @model_validator(mode="after")
    def _need_identity(self):
        if self.employee_id is None and not (self.system_account_id or "").strip():
            raise ValueError("须提供 employee_id 或 system_account_id")
        et = (self.event_type or "").strip().lower()
        if et not in {"grant", "revoke"}:
            raise ValueError("event_type 须为 grant 或 revoke")
        self.event_type = et
        return self
