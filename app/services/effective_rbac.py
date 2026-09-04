"""Effective roles = direct user roles ∪ position-bound roles (optional sync).

When sync_roles_from_position is true (default for demo):
  - Resolve position from SysUser.position_id, OR from linked Employee.position_id
  - Load PositionRole → SysRole and merge into effective roles for login /me / permission checks

Direct SysUserRole rows are never auto-deleted; position roles are merged at read time only.
"""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models.employee import Employee
from app.models.position import PositionRole
from app.models.sys_rbac import SysRole, SysUser


def is_sync_roles_from_position() -> bool:
    return bool(get_settings().sync_roles_from_position)


def resolve_position_id(db: Session, user: SysUser) -> int | None:
    if user.position_id:
        return user.position_id
    emp_id = user.employee_id
    if not emp_id:
        return None
    emp = db.get(Employee, emp_id)
    return emp.position_id if emp else None


def position_roles(db: Session, position_id: int | None) -> list[SysRole]:
    if not position_id:
        return []
    role_ids = [
        pr.role_id
        for pr in db.query(PositionRole).filter(PositionRole.position_id == position_id).all()
    ]
    if not role_ids:
        return []
    return (
        db.query(SysRole)
        .options(joinedload(SysRole.permissions))
        .filter(SysRole.id.in_(role_ids), SysRole.status == "active")
        .all()
    )


def effective_roles(db: Session, user: SysUser) -> list[SysRole]:
    """Union of direct roles and (optional) position roles. Deduped by role id."""
    seen: dict[int, SysRole] = {}
    for r in user.roles or []:
        if r.status == "active":
            seen[r.id] = r
    if is_sync_roles_from_position():
        pid = resolve_position_id(db, user)
        for r in position_roles(db, pid):
            seen[r.id] = r
    return list(seen.values())


def bind_user_employee(db: Session, user: SysUser, employee_id: int | None) -> None:
    """Keep SysUser.employee_id ↔ Employee.sys_user_id consistent both ways."""
    old_emp_id = user.employee_id
    if old_emp_id and old_emp_id != employee_id:
        old = db.get(Employee, old_emp_id)
        if old and old.sys_user_id == user.id:
            old.sys_user_id = None
    user.employee_id = employee_id
    if employee_id:
        emp = db.get(Employee, employee_id)
        if not emp:
            from fastapi import HTTPException

            raise HTTPException(400, detail="关联员工不存在")
        if emp.sys_user_id and emp.sys_user_id != user.id:
            other = db.get(SysUser, emp.sys_user_id)
            if other and other.employee_id == emp.id:
                other.employee_id = None
        emp.sys_user_id = user.id
        # align user position from employee if user has none
        if not user.position_id and emp.position_id:
            user.position_id = emp.position_id
