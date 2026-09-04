from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.recruiting import RecruitingReq
from app.schemas.recruiting import RecruitingCreate, RecruitingOut, RecruitingUpdate

router = APIRouter(
    prefix="/api/v1/recruiting", tags=["T04-recruiting"], dependencies=[Depends(require_api_key)]
)


@router.post("", response_model=RecruitingOut)
def create_req(body: RecruitingCreate, db: Session = Depends(get_db)):
    row = RecruitingReq(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[RecruitingOut])
def list_reqs(db: Session = Depends(get_db)):
    return db.query(RecruitingReq).all()


@router.get("/{item_id}", response_model=RecruitingOut)
def get_req(item_id: int, db: Session = Depends(get_db)):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="招聘需求不存在")
    return row


@router.patch("/{item_id}", response_model=RecruitingOut)
def update_req(item_id: int, body: RecruitingUpdate, db: Session = Depends(get_db)):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="招聘需求不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_req(item_id: int, db: Session = Depends(get_db)):
    row = db.get(RecruitingReq, item_id)
    if not row:
        raise HTTPException(404, detail="招聘需求不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
