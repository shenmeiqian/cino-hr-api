from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.employee import Department, Employee
from app.schemas.employee import (
    DepartmentCreate,
    DepartmentOut,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["T01-employees"], dependencies=[Depends(require_api_key)])


@router.post("/departments", response_model=DepartmentOut)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db)):
    row = Department(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()


@router.post("/employees", response_model=EmployeeOut)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db)):
    if db.query(Employee).filter(Employee.emp_no == body.emp_no).first():
        raise HTTPException(400, detail=f"工号已存在: {body.emp_no}")
    row = Employee(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    status: str | None = None,
    system_account_id: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Employee)
    if status:
        q = q.filter(Employee.status == status)
    if system_account_id:
        q = q.filter(Employee.system_account_id == system_account_id)
    return q.all()


@router.get("/employees/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: int, db: Session = Depends(get_db)):
    row = db.get(Employee, emp_id)
    if not row:
        raise HTTPException(404, detail="员工不存在")
    return row


@router.patch("/employees/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: int, body: EmployeeUpdate, db: Session = Depends(get_db)):
    row = db.get(Employee, emp_id)
    if not row:
        raise HTTPException(404, detail="员工不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/employees/{emp_id}")
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    row = db.get(Employee, emp_id)
    if not row:
        raise HTTPException(404, detail="员工不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除", "id": emp_id}
