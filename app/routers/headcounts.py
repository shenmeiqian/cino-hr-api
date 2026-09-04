from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.headcount import HeadcountPlan
from app.schemas.headcount import HeadcountCreate, HeadcountOut, HeadcountUpdate

router = APIRouter(prefix="/api/v1/headcounts", tags=["T02-headcounts"])


@router.post("", response_model=HeadcountOut)
def create_headcount(
    body: HeadcountCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    row = HeadcountPlan(**body.model_dump())
    if row.vacancy == 0 and row.planned_count:
        row.vacancy = max(0, row.planned_count - row.actual_count)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[HeadcountOut])
def list_headcounts(
    year_month: str | None = None,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.org")),
):
    q = db.query(HeadcountPlan)
    if year_month:
        q = q.filter(HeadcountPlan.year_month == year_month)
    return q.all()


@router.get("/{item_id}", response_model=HeadcountOut)
def get_headcount(
    item_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.org")),
):
    row = db.get(HeadcountPlan, item_id)
    if not row:
        raise HTTPException(404, detail="编制计划不存在")
    return row


@router.patch("/{item_id}", response_model=HeadcountOut)
def update_headcount(
    item_id: int,
    body: HeadcountUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    row = db.get(HeadcountPlan, item_id)
    if not row:
        raise HTTPException(404, detail="编制计划不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.vacancy = max(0, row.planned_count - row.actual_count)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_headcount(
    item_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    row = db.get(HeadcountPlan, item_id)
    if not row:
        raise HTTPException(404, detail="编制计划不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
