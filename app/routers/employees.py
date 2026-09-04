from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import AuthContext, hash_password, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.employee import Department, Employee
from app.models.sys_rbac import SysUser, SysUserRole
from app.schemas.employee import (
    DepartmentCreate,
    DepartmentOut,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
)
from app.services.effective_rbac import bind_user_employee

router = APIRouter(prefix="/api/v1", tags=["T01-employees"])


def _sync_user_employee(db: Session, emp: Employee, sys_user_id: int | None) -> None:
    """Keep Employee.sys_user_id ↔ SysUser.employee_id consistent both ways."""
    if emp.sys_user_id and emp.sys_user_id != sys_user_id:
        old = db.get(SysUser, emp.sys_user_id)
        if old and old.employee_id == emp.id:
            old.employee_id = None
    emp.sys_user_id = sys_user_id
    if sys_user_id:
        user = db.get(SysUser, sys_user_id)
        if not user:
            raise HTTPException(400, detail="关联用户不存在")
        if user.employee_id and user.employee_id != emp.id:
            other = db.get(Employee, user.employee_id)
            if other:
                other.sys_user_id = None
        user.employee_id = emp.id
        if not user.position_id and emp.position_id:
            user.position_id = emp.position_id


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
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    if db.query(Department).filter(Department.code == body.code).first():
        raise HTTPException(400, detail="部门编码已存在")
    row = Department(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_user_or_api_key)):
    return db.query(Department).order_by(Department.id).all()


@router.patch("/departments/{item_id}", response_model=DepartmentOut)
def update_department(
    item_id: int,
    body: DepartmentCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.org.write")),
):
    row = db.get(Department, item_id)
    if not row:
        raise HTTPException(404, detail="部门不存在")
    row.name = body.name
    row.parent_id = body.parent_id
    # code immutable once created unless unique
    if body.code != row.code:
        if db.query(Department).filter(Department.code == body.code, Department.id != item_id).first():
            raise HTTPException(400, detail="部门编码已存在")
        row.code = body.code
    db.commit()
    db.refresh(row)
    return row


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
    # keep linked user's position aligned when employee position changes
    if "position_id" in data and row.sys_user_id:
        u = db.get(SysUser, row.sys_user_id)
        if u:
            u.position_id = row.position_id
    db.commit()
    db.refresh(row)
    return _out(db, row)


class CreateSysUserFromEmployeeIn(BaseModel):
    username: str | None = None
    password: str = Field(default="ChangeMe123")
    role_ids: list[int] = Field(default_factory=list)


@router.post("/employees/{item_id}/create-sys-user", response_model=EmployeeOut)
def create_sys_user_from_employee(
    item_id: int,
    body: CreateSysUserFromEmployeeIn,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.employees.edit")),
):
    """Shortcut: create a SysUser from employee and bind both ways."""
    emp = db.get(Employee, item_id)
    if not emp:
        raise HTTPException(404, detail="员工不存在")
    if emp.sys_user_id:
        raise HTTPException(400, detail="该员工已绑定系统用户")
    username = body.username or f"u_{emp.emp_no}".lower()
    if db.query(SysUser).filter(SysUser.username == username).first():
        raise HTTPException(400, detail=f"用户名已存在: {username}")
    u = SysUser(
        username=username,
        display_name=emp.name,
        password_hash=hash_password(body.password),
        employee_id=emp.id,
        position_id=emp.position_id,
        phone=emp.phone,
        email=emp.email,
        status="active",
    )
    db.add(u)
    db.flush()
    for rid in body.role_ids:
        db.add(SysUserRole(user_id=u.id, role_id=rid))
    emp.sys_user_id = u.id
    db.commit()
    db.refresh(emp)
    return _out(db, emp)
