from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.attendance import AttendanceException
from app.schemas.attendance import AttendanceCreate, AttendanceOut, AttendanceUpdate

router = APIRouter(
    prefix="/api/v1/attendance-exceptions",
    tags=["T09-attendance"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=AttendanceOut)
def create_exc(body: AttendanceCreate, db: Session = Depends(get_db)):
    row = AttendanceException(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[AttendanceOut])
def list_exc(employee_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(AttendanceException)
    if employee_id:
        q = q.filter(AttendanceException.employee_id == employee_id)
    return q.all()


@router.get("/{item_id}", response_model=AttendanceOut)
def get_exc(item_id: int, db: Session = Depends(get_db)):
    row = db.get(AttendanceException, item_id)
    if not row:
        raise HTTPException(404, detail="考勤异常不存在")
    return row


@router.patch("/{item_id}", response_model=AttendanceOut)
def update_exc(item_id: int, body: AttendanceUpdate, db: Session = Depends(get_db)):
    row = db.get(AttendanceException, item_id)
    if not row:
        raise HTTPException(404, detail="考勤异常不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{item_id}")
def delete_exc(item_id: int, db: Session = Depends(get_db)):
    row = db.get(AttendanceException, item_id)
    if not row:
        raise HTTPException(404, detail="考勤异常不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": item_id}
