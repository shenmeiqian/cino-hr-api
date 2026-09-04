from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceOut

router = APIRouter(
    prefix="/api/v1/evidences", tags=["T14-evidences"], dependencies=[Depends(require_api_key)]
)


@router.post("", response_model=EvidenceOut)
def create_evidence(body: EvidenceCreate, db: Session = Depends(get_db)):
    row = Evidence(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[EvidenceOut])
def list_evidences(ref_type: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Evidence)
    if ref_type:
        q = q.filter(Evidence.ref_type == ref_type)
    return q.all()


@router.get("/{item_id}", response_model=EvidenceOut)
def get_evidence(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Evidence, item_id)
    if not row:
        raise HTTPException(404, detail="证据不存在")
    return row


@router.delete("/{item_id}")
def delete_evidence(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Evidence, item_id)
    if not row:
        raise HTTPException(404, detail="证据不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
