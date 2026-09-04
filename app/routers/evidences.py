from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceOut, EvidenceUpdate

router = APIRouter(
    prefix="/api/v1/evidences", tags=["T14-evidences"], dependencies=[Depends(require_user_or_api_key)]
)


@router.post("", response_model=EvidenceOut)
def create_evidence(body: EvidenceCreate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("btn.evidences.create"))):
    row = Evidence(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[EvidenceOut])
def list_evidences(ref_type: str | None = None, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.evidences"))):
    q = db.query(Evidence)
    if ref_type:
        q = q.filter(Evidence.ref_type == ref_type)
    return q.all()


@router.get("/{item_id}", response_model=EvidenceOut)
def get_evidence(item_id: int, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.evidences"))):
    row = db.get(Evidence, item_id)
    if not row:
        raise HTTPException(404, detail="证据不存在")
    return row


@router.patch("/{item_id}", response_model=EvidenceOut)
def update_evidence(item_id: int, body: EvidenceUpdate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("api.evidences.write"))):
    row = db.get(Evidence, item_id)
    if not row:
        raise HTTPException(404, detail="证据不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_evidence(item_id: int, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("api.evidences.write"))):
    row = db.get(Evidence, item_id)
    if not row:
        raise HTTPException(404, detail="证据不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
