from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.contract import Contract
from app.schemas.contract import ContractCreate, ContractOut, ContractUpdate

router = APIRouter(
    prefix="/api/v1/contracts", tags=["T06-contracts"], dependencies=[Depends(require_api_key)]
)


@router.post("", response_model=ContractOut)
def create_contract(body: ContractCreate, db: Session = Depends(get_db)):
    row = Contract(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[ContractOut])
def list_contracts(employee_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Contract)
    if employee_id:
        q = q.filter(Contract.employee_id == employee_id)
    return q.all()


@router.get("/{item_id}", response_model=ContractOut)
def get_contract(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Contract, item_id)
    if not row:
        raise HTTPException(404, detail="合同不存在")
    return row


@router.patch("/{item_id}", response_model=ContractOut)
def update_contract(item_id: int, body: ContractUpdate, db: Session = Depends(get_db)):
    row = db.get(Contract, item_id)
    if not row:
        raise HTTPException(404, detail="合同不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_contract(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Contract, item_id)
    if not row:
        raise HTTPException(404, detail="合同不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
