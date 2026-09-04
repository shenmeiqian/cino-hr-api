from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.onboarding import Onboarding
from app.schemas.onboarding import OnboardingCreate, OnboardingOut, OnboardingUpdate

router = APIRouter(
    prefix="/api/v1/onboarding", tags=["T05-onboarding"], dependencies=[Depends(require_api_key)]
)


@router.post("", response_model=OnboardingOut)
def create_onboarding(body: OnboardingCreate, db: Session = Depends(get_db)):
    row = Onboarding(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[OnboardingOut])
def list_onboarding(db: Session = Depends(get_db)):
    return db.query(Onboarding).all()


@router.get("/{item_id}", response_model=OnboardingOut)
def get_onboarding(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Onboarding, item_id)
    if not row:
        raise HTTPException(404, detail="入职记录不存在")
    return row


@router.patch("/{item_id}", response_model=OnboardingOut)
def update_onboarding(item_id: int, body: OnboardingUpdate, db: Session = Depends(get_db)):
    row = db.get(Onboarding, item_id)
    if not row:
        raise HTTPException(404, detail="入职记录不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_onboarding(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Onboarding, item_id)
    if not row:
        raise HTTPException(404, detail="入职记录不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
