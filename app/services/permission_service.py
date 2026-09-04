"""Permission grant/revoke business rules."""
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.permission import PermissionEvent
from app.models.training import Training

# Media contact 申请 wipe / outbound 时必须持有的有效培训
REQUIRED_MEDIA_COURSES = ("safety", "sop", "wipe_r2")
SENSITIVE_SCOPES = {"wipe", "outbound"}
CRITICAL_REVOKE_TRIGGERS = {"leave", "project_end"}


def _scopes_csv(scopes: list[str]) -> str:
    return ",".join(sorted({s.strip().lower() for s in scopes if s.strip()}))


def check_media_contact_training_gate(db: Session, employee: Employee, scopes: list[str]) -> None:
    """媒体联络人申请 wipe/outbound 时，须三项培训均 passed 且未过期，否则 403。"""
    normalized = {s.strip().lower() for s in scopes}
    needs_gate = employee.is_media_contact and bool(normalized & SENSITIVE_SCOPES)
    if not needs_gate:
        return

    today = date.today()
    missing: list[str] = []
    for course in REQUIRED_MEDIA_COURSES:
        row = (
            db.query(Training)
            .filter(
                Training.employee_id == employee.id,
                Training.course_code == course,
                Training.status == "passed",
                Training.valid_until.isnot(None),
                Training.valid_until >= today,
            )
            .order_by(Training.valid_until.desc())
            .first()
        )
        if not row:
            missing.append(course)

    if missing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"媒体联络人申请 wipe/outbound 权限前须完成并通过有效培训："
                f"{', '.join(REQUIRED_MEDIA_COURSES)}。"
                f"当前缺失或已过期：{', '.join(missing)}"
            ),
        )


def grant_permission(
    db: Session,
    *,
    employee_id: int,
    scopes: list[str],
    reason: str | None,
    operator: str | None,
) -> PermissionEvent:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail=f"员工不存在: id={employee_id}")

    check_media_contact_training_gate(db, employee, scopes)

    event = PermissionEvent(
        employee_id=employee_id,
        event_type="grant",
        scopes=_scopes_csv(scopes),
        reason=reason,
        trigger="normal",
        status="done",
        due_at=None,
        completed_at=datetime.utcnow(),
        operator=operator,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def revoke_permission(
    db: Session,
    *,
    employee_id: int,
    scopes: list[str],
    reason: str | None,
    trigger: str | None,
    operator: str | None,
) -> PermissionEvent:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail=f"员工不存在: id={employee_id}")

    now = datetime.utcnow()
    trigger_norm = (trigger or "normal").strip().lower()
    # 关键岗位 + 离职/项目结束 → due_at = T+0（立即）
    due_at = None
    status_val = "done"
    completed_at = now
    if employee.is_critical_role and trigger_norm in CRITICAL_REVOKE_TRIGGERS:
        due_at = now  # T+0
        status_val = "pending"
        completed_at = None

    event = PermissionEvent(
        employee_id=employee_id,
        event_type="revoke",
        scopes=_scopes_csv(scopes),
        reason=reason,
        trigger=trigger_norm,
        status=status_val,
        due_at=due_at,
        completed_at=completed_at,
        operator=operator,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
