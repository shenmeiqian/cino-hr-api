from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.employee import Department, Employee
from app.models.position import PositionRole
from app.models.sys_rbac import SysRole, SysUser, SysUserRole
from app.schemas.employee import (
    DepartmentCreate,
    DepartmentOut,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["T01-employees"])


def _sync_user_employee(db: Session, emp: Employee, sys_user_id: int | None) -> None:
    """Keep Employee.sys_user_id <-> SysUser.employee_id consistent; sync position roles."""
    # clear old link
    if emp.sys_user_id and emp.sys_user_id != sys_user_id:
        old = db.get(SysUser, emp.sys_user_id)
        if old and old.employee_id == emp.id:
            old.employee_id = None
    emp.sys_user_id = sys_user_id
    if sys_user_id:
        user = db.get(SysUser, sys_user_id)
        if not user:
            raise HTTPException(400, detail="关联用户不存在")
        # if user bound to another emp, clear that
        if user.employee_id and user.employee_id != emp.id:
            other = db.get(Employee, user.employee_id)
            if other:
                other.sys_user_id = None
        user.employee_id = emp.id
        # sync roles from position
        if emp.position_id:
            role_ids = [
                pr.role_id
                for pr in db.query(PositionRole).filter(PositionRole.position_id == emp.position_id).all()
            ]
            for rid in role_ids:
                exists = (
                    db.query(SysUserRole)
                    .filter(SysUserRole.user_id == user.id, SysUserRole.role_id == rid)
                    .first()
                )
                if not exists:
                    db.add(SysUserRole(user_id=user.id, role_id=rid))


def _out(db: Session, row: Employee) -> EmployeeOut:
    data = EmployeeOut.model_validate(row)
    if row.sys_user_id:
        u = db.get(SysUser, row.sys_user_id)
        data.sys_username = u.username if u else None
    return data


@router.post("/departments", response_model=DepartmentOut)
def create_department(
    body: DepartmentCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_user_or_api_key),
):
    row = Department(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_user_or_api_key)):
    return db.query(Department).all()


@router.post("/employees", response_model=EmployeeOut)
def create_employee(
    body: EmployeeCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.employees.create")),
):
    if db.query(Employee).filter(Employee.emp_no == body.emp_no).first():
        raise HTTPException(400, detail=f"工号已存在: {body.emp_no}")
    data = body.model_dump()
    sys_user_id = data.pop("sys_user_id", None)
    row = Employee(**data)
    db.add(row)
    db.flush()
    if sys_user_id is not None:
        _sync_user_employee(db, row, sys_user_id)
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.employees")),
    status: str | None = Query(default=None),
):
    q = db.query(Employee)
    if status:
        q = q.filter(Employee.status == status)
    return [_out(db, r) for r in q.order_by(Employee.id).all()]


@router.get("/employees/{item_id}", response_model=EmployeeOut)
def get_employee(item_id: int, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.employees"))):
    row = db.get(Employee, item_id)
    if not row:
        raise HTTPException(404, detail="员工不存在")
    return _out(db, row)


@router.patch("/employees/{item_id}", response_model=EmployeeOut)
def update_employee(
    item_id: int,
    body: EmployeeUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.employees.edit")),
):
    row = db.get(Employee, item_id)
    if not row:
        raise HTTPException(404, detail="员工不存在")
    data = body.model_dump(exclude_unset=True)
    sys_user_id = data.pop("sys_user_id", "__omit__")
    for k, v in data.items():
        setattr(row, k, v)
    if sys_user_id != "__omit__":
        _sync_user_employee(db, row, sys_user_id)
    elif "position_id" in data and row.sys_user_id and row.position_id:
        _sync_user_employee(db, row, row.sys_user_id)
    db.commit()
    db.refresh(row)
    return _out(db, row)
