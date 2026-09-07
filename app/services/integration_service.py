"""HR ↔ 综合系统 3.0 对接逻辑（用户同步、培训闸门校验、待回收、权限回调）。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models.employee import Department, Employee
from app.models.integration import IntegrationConfig, IntegrationSyncLog
from app.models.permission import PermissionEvent
from app.models.sys_rbac import SysUser
from app.schemas.integration import (
    IntegrationConfigOut,
    LastSyncSlice,
    PermissionCallbackIn,
    PendingRevokeOut,
    SyncStatusOut,
    SyncUserItemOut,
    SyncUsersOut,
    Sys3UserIn,
    ValidateTrainingOut,
)
from app.services.permission_service import (
    CRITICAL_REVOKE_TRIGGERS,
    REQUIRED_MEDIA_COURSES,
    inspect_media_training_gate,
    scopes_csv,
)

LEFT_STATUSES = {"leave", "resigned", "left"}
ALLOWED_USER_STATUS = {"active", "frozen", "disabled"}


def _map_user_status(raw: str) -> str:
    s = (raw or "active").strip().lower()
    if s in ALLOWED_USER_STATUS:
        return s
    if s in LEFT_STATUSES or s in {"inactive", "disabled"}:
        return "disabled"
    return "active"


def resolve_employee(
    db: Session,
    *,
    employee_id: int | None = None,
    system_account_id: str | None = None,
) -> Employee:
    if employee_id is not None:
        emp = db.get(Employee, employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail=f"员工不存在: id={employee_id}")
        return emp
    sid = (system_account_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="须提供 employee_id 或 system_account_id")
    emp = db.query(Employee).filter(Employee.system_account_id == sid).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"未找到绑定账号 {sid} 的员工")
    return emp


def sync_status(db: Session) -> SyncStatusOut:
    cfg = db.query(IntegrationConfig).order_by(IntegrationConfig.id.asc()).first()
    last_syncs: list[LastSyncSlice] = []
    for sync_type in ("users", "permissions", "full"):
        row = (
            db.query(IntegrationSyncLog)
            .filter(IntegrationSyncLog.sync_type == sync_type)
            .order_by(IntegrationSyncLog.id.desc())
            .first()
        )
        if row:
            last_syncs.append(
                LastSyncSlice(
                    sync_type=sync_type,
                    status=row.status,
                    finished_at=row.finished_at,
                    count_in=row.count_in,
                    count_created=row.count_created,
                    count_updated=row.count_updated,
                    count_linked=row.count_linked,
                    message=row.message,
                )
            )
        else:
            last_syncs.append(LastSyncSlice(sync_type=sync_type))

    total_emp = db.query(func.count(Employee.id)).scalar() or 0
    linked = (
        db.query(func.count(Employee.id))
        .filter(Employee.system_account_id.isnot(None), Employee.system_account_id != "")
        .scalar()
        or 0
    )
    pending = _pending_revoke_count(db)
    counts = {
        "sys_users": db.query(func.count(SysUser.id)).scalar() or 0,
        "employees": total_emp,
        "employees_linked": linked,
        "employees_unlinked": max(0, total_emp - linked),
        "pending_revokes": pending,
        "sync_logs": db.query(func.count(IntegrationSyncLog.id)).scalar() or 0,
    }
    return SyncStatusOut(
        config=IntegrationConfigOut.model_validate(cfg) if cfg else None,
        last_syncs=last_syncs,
        counts=counts,
    )


def _find_employee_for_sys3(db: Session, user: Sys3UserIn, sys_user: SysUser) -> Optional[Employee]:
    emp = db.query(Employee).filter(Employee.system_account_id == user.id).first()
    if emp:
        return emp
    if sys_user.employee_id:
        emp = db.get(Employee, sys_user.employee_id)
        if emp:
            return emp
    emp = db.query(Employee).filter(Employee.emp_no == user.username).first()
    if emp:
        return emp
    return None


def sync_users(db: Session, users: list[Sys3UserIn]) -> SyncUsersOut:
    now = datetime.utcnow()
    created = updated = linked = 0
    items: list[SyncUserItemOut] = []

    for u in users:
        username = u.username.strip()
        if not username:
            items.append(
                SyncUserItemOut(
                    id=u.id,
                    username=u.username,
                    action="skipped",
                    sys_user_id=0,
                    linked=False,
                    message="username 为空",
                )
            )
            continue

        row = db.query(SysUser).filter(SysUser.username == username).first()
        mapped_status = _map_user_status(u.status)
        action = "updated"
        if not row:
            row = SysUser(
                username=username,
                display_name=u.display_name,
                # 3.0 不同步密码；本地不可用随机口令，避免伪造 3.0 凭证
                password_hash=hash_password(f"sync-placeholder-{username}"),
                status=mapped_status,
            )
            db.add(row)
            db.flush()
            action = "created"
            created += 1
        else:
            row.display_name = u.display_name
            row.status = mapped_status
            updated += 1

        emp = _find_employee_for_sys3(db, u, row)
        emp_id = None
        linked_flag = False
        msg = None
        if emp:
            emp.system_account_id = u.id
            emp.sys_user_id = row.id
            row.employee_id = emp.id
            if emp.position_id and not row.position_id:
                row.position_id = emp.position_id
            if u.dept_code:
                dept = db.query(Department).filter(Department.code == u.dept_code).first()
                if dept:
                    emp.dept_id = dept.id
            emp_id = emp.id
            linked_flag = True
            linked += 1
            msg = "已绑定员工 system_account_id"
        else:
            msg = "未匹配到员工，仅 upsert SysUser"

        items.append(
            SyncUserItemOut(
                id=u.id,
                username=username,
                action=action,
                sys_user_id=row.id,
                employee_id=emp_id,
                system_account_id=u.id if emp else None,
                linked=linked_flag,
                message=msg,
            )
        )

    log = IntegrationSyncLog(
        sync_type="users",
        status="success" if created + updated == len(users) else "partial",
        started_at=now,
        finished_at=datetime.utcnow(),
        count_in=len(users),
        count_created=created,
        count_updated=updated,
        count_linked=linked,
        message=f"upsert SysUser created={created} updated={updated} linked={linked}",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return SyncUsersOut(
        ok=True,
        sync_log_id=log.id,
        created=created,
        updated=updated,
        linked=linked,
        items=items,
    )


def validate_training_before_grant(
    db: Session,
    *,
    employee_id: int | None,
    system_account_id: str | None,
    scopes: list[str],
) -> ValidateTrainingOut:
    emp = resolve_employee(db, employee_id=employee_id, system_account_id=system_account_id)
    gate_applied, missing = inspect_media_training_gate(db, emp, scopes)
    ok = not missing
    if not gate_applied:
        detail = "无需媒体联络人培训闸门（非媒体联络人或 scopes 不含 wipe/outbound）"
    elif ok:
        detail = (
            f"媒体联络人培训闸门通过：{', '.join(REQUIRED_MEDIA_COURSES)} 均 passed 且未过期"
        )
    else:
        detail = (
            f"媒体联络人申请 wipe/outbound 前须完成并通过有效培训："
            f"{', '.join(REQUIRED_MEDIA_COURSES)}。当前缺失或已过期：{', '.join(missing)}"
        )
    return ValidateTrainingOut(
        ok=ok,
        gate_applied=gate_applied,
        employee_id=emp.id,
        emp_no=emp.emp_no,
        name=emp.name,
        system_account_id=emp.system_account_id,
        is_media_contact=emp.is_media_contact,
        scopes=scopes,
        required_courses=list(REQUIRED_MEDIA_COURSES) if gate_applied else [],
        missing_courses=missing,
        detail=detail,
    )


def _pending_revoke_count(db: Session) -> int:
    return len(list_pending_revokes(db))


def list_pending_revokes(db: Session) -> list[PendingRevokeOut]:
    """关键岗离职/项目结束须 T+0 停权：已有 pending 事件，或已离职尚未完成回收。"""
    now = datetime.utcnow()
    today = date.today()
    seen_emp: set[int] = set()
    out: list[PendingRevokeOut] = []

    pending_events = (
        db.query(PermissionEvent)
        .filter(
            PermissionEvent.event_type == "revoke",
            PermissionEvent.status == "pending",
        )
        .order_by(PermissionEvent.id.desc())
        .all()
    )
    for ev in pending_events:
        emp = db.get(Employee, ev.employee_id)
        if not emp:
            continue
        reason = ev.trigger if ev.trigger in CRITICAL_REVOKE_TRIGGERS else (ev.trigger or "pending")
        out.append(
            PendingRevokeOut(
                employee_id=emp.id,
                emp_no=emp.emp_no,
                name=emp.name,
                system_account_id=emp.system_account_id,
                status=emp.status,
                is_critical_role=emp.is_critical_role,
                reason=reason,
                due_at=ev.due_at or now,
                pending_event_id=ev.id,
                scopes=ev.scopes,
            )
        )
        seen_emp.add(emp.id)

    leavers = (
        db.query(Employee)
        .filter(Employee.is_critical_role.is_(True))
        .all()
    )
    for emp in leavers:
        if emp.id in seen_emp:
            continue
        left = (emp.status or "").lower() in LEFT_STATUSES
        dated = emp.leave_date is not None and emp.leave_date <= today
        if not (left or dated):
            continue
        done = (
            db.query(PermissionEvent)
            .filter(
                PermissionEvent.employee_id == emp.id,
                PermissionEvent.event_type == "revoke",
                PermissionEvent.trigger.in_(list(CRITICAL_REVOKE_TRIGGERS)),
                PermissionEvent.status == "done",
            )
            .first()
        )
        if done:
            continue
        out.append(
            PendingRevokeOut(
                employee_id=emp.id,
                emp_no=emp.emp_no,
                name=emp.name,
                system_account_id=emp.system_account_id,
                status=emp.status,
                is_critical_role=True,
                reason="leave",
                due_at=now,
                pending_event_id=None,
                scopes=None,
            )
        )
    return out


def apply_permission_callback(db: Session, body: PermissionCallbackIn) -> PermissionEvent:
    emp = resolve_employee(db, employee_id=body.employee_id, system_account_id=body.system_account_id)
    now = datetime.utcnow()
    csv = scopes_csv(body.scopes)
    status_val = (body.status or "done").strip().lower()
    if status_val not in {"done", "failed", "pending"}:
        status_val = "done"
    trigger = (body.trigger or "normal").strip().lower()
    reason = body.reason or ""
    if body.external_ref:
        extra = f"3.0 ref={body.external_ref}"
        reason = f"{reason} ({extra})".strip() if reason else extra

    pending = (
        db.query(PermissionEvent)
        .filter(
            PermissionEvent.employee_id == emp.id,
            PermissionEvent.event_type == body.event_type,
            PermissionEvent.status == "pending",
        )
        .order_by(PermissionEvent.id.desc())
        .first()
    )
    if pending:
        pending.status = status_val
        pending.completed_at = now if status_val == "done" else pending.completed_at
        pending.operator = body.operator or pending.operator
        if csv:
            pending.scopes = csv
        if reason:
            pending.reason = reason
        if body.trigger:
            pending.trigger = trigger
        db.commit()
        db.refresh(pending)
        _write_callback_log(db, body.event_type, 1)
        return pending

    event = PermissionEvent(
        employee_id=emp.id,
        event_type=body.event_type,
        scopes=csv,
        reason=reason or "综合系统3.0权限回调",
        trigger=trigger,
        status=status_val,
        due_at=None,
        completed_at=now if status_val == "done" else None,
        operator=body.operator or "sys3-callback",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    _write_callback_log(db, body.event_type, 1)
    return event


def _write_callback_log(db: Session, event_type: str, n: int) -> None:
    log = IntegrationSyncLog(
        sync_type="permissions",
        status="success",
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        count_in=n,
        count_created=n,
        count_updated=0,
        count_linked=0,
        message=f"permission-callback {event_type}",
    )
    db.add(log)
    db.commit()


def seed_integration(db: Session) -> None:
    """演示配置 + 示例同步日志。不含任何真实 3.0 凭证。"""
    cfg = db.query(IntegrationConfig).filter(IntegrationConfig.name.like("%综合系统%")).first()
    if not cfg:
        db.add(
            IntegrationConfig(
                name="综合系统3.0（演示）",
                base_url="https://sys3.example.invalid",
                auth_mode="api_key",
                credential_hint="3.0 调用本服务使用 X-API-Key（默认 demo-key）；本库不保存 3.0 密钥",
                status="demo",
                remark="占位对接配置。Web 管理端通过本 API 查询同步状态、推送用户、校验培训闸门与接收权限回调。",
            )
        )
        print("Seed integration config: 综合系统3.0（演示）")

    if db.query(IntegrationSyncLog).count() == 0:
        linked = (
            db.query(func.count(Employee.id))
            .filter(Employee.system_account_id.isnot(None), Employee.system_account_id != "")
            .scalar()
            or 0
        )
        now = datetime.utcnow()
        db.add(
            IntegrationSyncLog(
                sync_type="users",
                status="success",
                started_at=now,
                finished_at=now,
                count_in=linked,
                count_created=0,
                count_updated=linked,
                count_linked=linked,
                message="seed 示例：花名册已预置 sys3-media-1001 等账号绑定",
            )
        )
        print("Seed integration sync log: users sample")
    db.commit()
