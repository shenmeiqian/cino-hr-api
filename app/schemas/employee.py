from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DepartmentCreate(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None


class DepartmentOut(ORMModel):
    id: int
    code: str
    name: str
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None


class EmployeeCreate(BaseModel):
    emp_no: str
    name: str
    dept_id: Optional[int] = None
    position_id: Optional[int] = None
    system_account_id: Optional[str] = Field(None, description="综合系统3.0账号ID绑定")
    sys_user_id: Optional[int] = Field(None, description="关联本地 SysUser")
    status: str = "active"
    hire_date: Optional[date] = None
    leave_date: Optional[date] = None
    is_media_contact: bool = False
    is_critical_role: bool = False
    phone: Optional[str] = None
    email: Optional[str] = None
    remark: Optional[str] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    dept_id: Optional[int] = None
    position_id: Optional[int] = None
    system_account_id: Optional[str] = None
    sys_user_id: Optional[int] = None
    status: Optional[str] = None
    hire_date: Optional[date] = None
    leave_date: Optional[date] = None
    is_media_contact: Optional[bool] = None
    is_critical_role: Optional[bool] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    remark: Optional[str] = None


class EmployeeOut(ORMModel):
    id: int
    emp_no: str
    name: str
    dept_id: Optional[int] = None
    position_id: Optional[int] = None
    system_account_id: Optional[str] = None
    sys_user_id: Optional[int] = None
    sys_username: Optional[str] = None
    status: str
    hire_date: Optional[date] = None
    leave_date: Optional[date] = None
    is_media_contact: bool
    is_critical_role: bool
    phone: Optional[str] = None
    email: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
