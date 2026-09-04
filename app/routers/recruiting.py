"""入职业务闭环 API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.recruiting import RecruitingReq
from app.schemas.recruiting import (
    PipelineAdvanceIn,
    RecruitingCreate,
    RecruitingOut,
    RecruitingUpdate,
)
from app.services.pipeline_service import advance, enrich

router = APIRouter(prefix="/api/v1/recruiting", tags=["hire-pipeline"])


def _out(db: Session, row: RecruitingReq) -> RecruitingOut:
    extra = enrich(db, row)
    data = RecruitingOut.model_validate(row)
    data.grant_status = extra["grant_status"]
    data.timeline = extra["timeline"]
    return data


@router.post("", response_model=RecruitingOut)
def create_req(
    body: RecruitingCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.recruiting.create")),
):
    row = RecruitingReq(**body.model_dump())
    if not row.stage:
        row.stage = "headcount"
    if not row.status or row.status == "open":
        row.status = "draft"
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.get("", response_model=list[RecruitingOut])
def list_reqs(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.recruiting")),
):
    rows = db.query(RecruitingReq).order_by(RecruitingReq.id.desc()).all()
    return [_out(db, r) for r in rows]


@router.get("/stats/grant")
def grant_stats(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_user_or_api_key),
):
    """看板：待开权/已开权/培训闸门失败 — 自动统计."""
    from app.models.employee import Employee
    from app.services.pipeline_service import grant_status_for_employee

    counts = {"ready": 0, "granted": 0, "pending_train": 0, "n/a": 0}
    for emp in db.query(Employee).filter(Employee.status == "active").all():
        s = grant_status_for_employee(db, emp)
        counts[s] = counts.get(s, 0) + 1
    return {"grant_stats": counts}


@router.get("/{item_id}", response_model=RecruitingOut)
def get_req(
    item_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.recruiting")),
):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="入职闭环单不存在")
    return _out(db, row)


@router.patch("/{item_id}", response_model=RecruitingOut)
def update_req(
    item_id: int,
    body: RecruitingUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.recruiting.create")),
):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="入职闭环单不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.post("/{item_id}/advance", response_model=RecruitingOut)
def advance_pipeline(
    item_id: int,
    body: PipelineAdvanceIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_perm("btn.recruiting.submit")),
):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="入职闭环单不存在")
    actor = "api-key" if auth.is_api_key else (auth.user.username if auth.user else "user")
    row = advance(db, row, body.action, body.model_dump(), actor=actor)
    return _out(db, row)


@router.delete("/{item_id}")
def delete_req(
    item_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.recruiting.create")),
):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="入职闭环单不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
