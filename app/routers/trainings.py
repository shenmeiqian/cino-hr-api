from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.training import Training
from app.schemas.training import TrainingCreate, TrainingOut, TrainingUpdate

router = APIRouter(
    prefix="/api/v1/trainings", tags=["T07-trainings"], dependencies=[Depends(require_user_or_api_key)]
)


@router.post("", response_model=TrainingOut)
def create_training(
    body: TrainingCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.trainings.create")),
):
    row = Training(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[TrainingOut])
def list_trainings(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.trainings")),
):
    q = db.query(Training)
    if employee_id:
        q = q.filter(Training.employee_id == employee_id)
    return q.all()


@router.get("/{item_id}", response_model=TrainingOut)
def get_training(
    item_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.trainings")),
):
    row = db.get(Training, item_id)
    if not row:
        raise HTTPException(404, detail="培训记录不存在")
    return row


@router.patch("/{item_id}", response_model=TrainingOut)
def update_training(
    item_id: int,
    body: TrainingUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.trainings.pass")),
):
    row = db.get(Training, item_id)
    if not row:
        raise HTTPException(404, detail="培训记录不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_training(
    item_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.trainings.write")),
):
    row = db.get(Training, item_id)
    if not row:
        raise HTTPException(404, detail="培训记录不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
