from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.position import Position, PositionClause, PositionRole
from app.models.sys_rbac import SysRole
from app.schemas.position import PositionCreate, PositionOut, PositionUpdate

router = APIRouter(prefix="/api/v1", tags=["T03-positions"])


def _out(db: Session, row: Position) -> PositionOut:
    prs = db.query(PositionRole).filter(PositionRole.position_id == row.id).all()
    role_ids = [p.role_id for p in prs]
    codes = []
    for rid in role_ids:
        r = db.get(SysRole, rid)
        if r:
            codes.append(r.code)
    data = PositionOut.model_validate(row)
    data.role_ids = role_ids
    data.role_codes = codes
    return data


def _set_roles(db: Session, position_id: int, role_ids: list[int]) -> None:
    db.query(PositionRole).filter(PositionRole.position_id == position_id).delete()
    for rid in role_ids:
        if not db.get(SysRole, rid):
            raise HTTPException(400, detail=f"角色不存在: {rid}")
        db.add(PositionRole(position_id=position_id, role_id=rid))


@router.post("/positions", response_model=PositionOut)
def create_position(
    body: PositionCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    if db.query(Position).filter(Position.code == body.code).first():
        raise HTTPException(400, detail="岗位编码已存在")
    data = body.model_dump()
    clauses = data.pop("clauses", [])
    role_ids = data.pop("role_ids", [])
    row = Position(**data)
    db.add(row)
    db.flush()
    for c in clauses:
        db.add(PositionClause(position_id=row.id, **c))
    if role_ids:
        _set_roles(db, row.id, role_ids)
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.get("/positions", response_model=list[PositionOut])
def list_positions(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_user_or_api_key)):  # used by user form too
    return [_out(db, r) for r in db.query(Position).order_by(Position.id).all()]


@router.get("/positions/{item_id}", response_model=PositionOut)
def get_position(item_id: int, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_user_or_api_key)):
    row = db.get(Position, item_id)
    if not row:
        raise HTTPException(404, detail="岗位不存在")
    return _out(db, row)


@router.patch("/positions/{item_id}", response_model=PositionOut)
def update_position(
    item_id: int,
    body: PositionUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    row = db.get(Position, item_id)
    if not row:
        raise HTTPException(404, detail="岗位不存在")
    data = body.model_dump(exclude_unset=True)
    role_ids = data.pop("role_ids", None)
    for k, v in data.items():
        setattr(row, k, v)
    if role_ids is not None:
        _set_roles(db, row.id, role_ids)
    db.commit()
    db.refresh(row)
    return _out(db, row)
