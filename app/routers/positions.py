from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.position import Position, PositionClause
from app.schemas.position import (
    PositionClauseCreate,
    PositionClauseOut,
    PositionCreate,
    PositionOut,
    PositionUpdate,
)

router = APIRouter(
    prefix="/api/v1/positions", tags=["T03-positions"], dependencies=[Depends(require_api_key)]
)


@router.post("", response_model=PositionOut)
def create_position(body: PositionCreate, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"clauses"})
    row = Position(**data)
    db.add(row)
    db.flush()
    for c in body.clauses:
        db.add(PositionClause(position_id=row.id, **c.model_dump()))
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[PositionOut])
def list_positions(db: Session = Depends(get_db)):
    return db.query(Position).all()


@router.get("/{item_id}", response_model=PositionOut)
def get_position(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Position, item_id)
    if not row:
        raise HTTPException(404, detail="岗位不存在")
    return row


@router.patch("/{item_id}", response_model=PositionOut)
def update_position(item_id: int, body: PositionUpdate, db: Session = Depends(get_db)):
    row = db.get(Position, item_id)
    if not row:
        raise HTTPException(404, detail="岗位不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{item_id}/clauses", response_model=PositionClauseOut)
def add_clause(item_id: int, body: PositionClauseCreate, db: Session = Depends(get_db)):
    if not db.get(Position, item_id):
        raise HTTPException(404, detail="岗位不存在")
    row = PositionClause(position_id=item_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_position(item_id: int, db: Session = Depends(get_db)):
    row = db.get(Position, item_id)
    if not row:
        raise HTTPException(404, detail="岗位不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
