from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LoginIn(BaseModel):
    username: str
    password: str


class UserBrief(ORMModel):
    id: int
    username: str
    display_name: str
    employee_id: Optional[int] = None
    position_id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str
    last_login_at: Optional[datetime] = None


class LoginOut(BaseModel):
    token: str
    user: UserBrief
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class MeOut(BaseModel):
    user: UserBrief
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    is_api_key: bool = False


class SysUserCreate(BaseModel):
    username: str
    display_name: str
    password: str
    employee_id: Optional[int] = None
    position_id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "active"
    role_ids: list[int] = Field(default_factory=list)


class SysUserUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    employee_id: Optional[int] = None
    position_id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    role_ids: Optional[list[int]] = None


class SysUserOut(ORMModel):
    id: int
    username: str
    display_name: str
    employee_id: Optional[int] = None
    position_id: Optional[int] = None
    position_code: Optional[str] = None
    position_title: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    role_ids: list[int] = Field(default_factory=list)
    role_codes: list[str] = Field(default_factory=list)


class SysRoleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    permission_ids: list[int] = Field(default_factory=list)


class SysRoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    permission_ids: Optional[list[int]] = None


class SysRoleOut(ORMModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    status: str
    permission_ids: list[int] = Field(default_factory=list)
    permission_codes: list[str] = Field(default_factory=list)


class SysPermissionCreate(BaseModel):
    code: str
    name: str
    type: str = "button"
    parent_id: Optional[int] = None
    sort_order: int = 0


class SysPermissionOut(ORMModel):
    id: int
    code: str
    name: str
    type: str
    parent_id: Optional[int] = None
    sort_order: int = 0


class PermTreeNode(BaseModel):
    id: int
    code: str
    name: str
    type: str
    parent_id: Optional[int] = None
    sort_order: int = 0
    children: list["PermTreeNode"] = Field(default_factory=list)


class ButtonPermBrief(BaseModel):
    code: str
    name: str


class SysMenuCreate(BaseModel):
    parent_id: Optional[int] = None
    title: str
    path: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    permission_code: str
    visible: bool = True
    component: Optional[str] = None


class SysMenuUpdate(BaseModel):
    parent_id: Optional[int] = None
    title: Optional[str] = None
    path: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    permission_code: Optional[str] = None
    visible: Optional[bool] = None
    component: Optional[str] = None


class SysMenuOut(ORMModel):
    id: int
    parent_id: Optional[int] = None
    title: str
    path: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    permission_code: str
    visible: bool = True
    component: Optional[str] = None
    # button permissions under this menu's permission_code (documentation / config)
    button_perms: list[ButtonPermBrief] = Field(default_factory=list)
    children: list["SysMenuOut"] = Field(default_factory=list)


class WorkflowSubmitIn(BaseModel):
    business_type: str
    business_id: int
    definition_id: Optional[int] = None
    definition_code: Optional[str] = None


class WorkflowTodoOut(ORMModel):
    id: int
    definition_id: int
    definition_code: Optional[str] = None
    definition_name: Optional[str] = None
    business_type: str
    business_id: int
    status: str
    current_node_id: Optional[str] = None
    current_node_label: Optional[str] = None
    approver_role: Optional[str] = None
    created_at: Optional[datetime] = None
