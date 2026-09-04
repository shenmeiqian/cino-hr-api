from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.permission import PermissionEvent
from app.schemas.permission import PermissionEventOut, PermissionGrantIn, PermissionRevokeIn
from app.services.permission_service import grant_permission, revoke_permission

router = APIRouter(
    prefix="/api/v1/permissions",
    tags=["T08-permissions"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/grant", response_model=PermissionEventOut)
def grant(body: PermissionGrantIn, db: Session = Depends(get_db)):
    """授予权限。媒体联络人申请 wipe/outbound 须通过 safety/sop/wipe_r2 有效培训。"""
    return grant_permission(
        db,
        employee_id=body.employee_id,
        scopes=body.scopes,
        reason=body.reason,
        operator=body.operator,
    )


@router.post("/revoke", response_model=PermissionEventOut)
def revoke(body: PermissionRevokeIn, db: Session = Depends(get_db)):
    """回收权限。关键岗位因 leave/project_end 触发时 due_at=T+0。"""
    return revoke_permission(
        db,
        employee_id=body.employee_id,
        scopes=body.scopes,
        reason=body.reason,
        trigger=body.trigger,
        operator=body.operator,
    )


@router.get("/events", response_model=list[PermissionEventOut])
def list_events(employee_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(PermissionEvent)
    if employee_id:
        q = q.filter(PermissionEvent.employee_id == employee_id)
    return q.order_by(PermissionEvent.id.desc()).all()
