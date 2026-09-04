"""Admin CRUD: users / roles / permissions tree / dynamic menus."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import AuthContext, hash_password, require_perm, require_user_or_api_key, revoke_user_tokens
from app.database import get_db
from app.models.employee import Employee
from app.models.position import Position
from app.services.effective_rbac import bind_user_employee
from app.models.sys_menu import SysMenu
from app.models.sys_rbac import (
    SysPermission,
    SysRole,
    SysRolePermission,
    SysUser,
    SysUserRole,
)
from app.schemas.sys_rbac import (
    ButtonPermBrief,
    PermTreeNode,
    SysMenuCreate,
    SysMenuOut,
    SysMenuUpdate,
    SysPermissionCreate,
    SysPermissionOut,
    SysRoleCreate,
    SysRoleOut,
    SysRoleUpdate,
    SysUserCreate,
    SysUserOut,
    SysUserUpdate,
)

router = APIRouter(prefix="/api/v1/sys", tags=["sys-rbac"])

ALLOWED_USER_STATUS = {"active", "frozen", "disabled"}


def _position_meta(db: Session, position_id: int | None) -> tuple[str | None, str | None]:
    if not position_id:
        return None, None
    pos = db.get(Position, position_id)
    if not pos:
        return None, None
    return pos.code, pos.title


def _user_out(db: Session, u: SysUser) -> SysUserOut:
    roles = u.roles or []
    code, title = _position_meta(db, u.position_id)
    emp_name = emp_no = None
    if u.employee_id:
        emp = db.get(Employee, u.employee_id)
        if emp:
            emp_name, emp_no = emp.name, emp.emp_no
    return SysUserOut(
        id=u.id,
        username=u.username,
        display_name=u.display_name,
        employee_id=u.employee_id,
        employee_name=emp_name,
        employee_no=emp_no,
        position_id=u.position_id,
        position_code=code,
        position_title=title,
        phone=getattr(u, "phone", None),
        email=getattr(u, "email", None),
        status=u.status,
        last_login_at=getattr(u, "last_login_at", None),
        created_at=u.created_at,
        role_ids=[r.id for r in roles],
        role_codes=[r.code for r in roles],
    )


def _role_out(r: SysRole) -> SysRoleOut:
    perms = r.permissions or []
    return SysRoleOut(
        id=r.id,
        code=r.code,
        name=r.name,
        description=r.description,
        status=r.status,
        permission_ids=[p.id for p in perms],
        permission_codes=[p.code for p in perms],
    )


def _button_perms_index(db: Session) -> dict[str, list[ButtonPermBrief]]:
    """Map menu permission code -> list of child button perms."""
    rows = db.query(SysPermission).order_by(SysPermission.sort_order, SysPermission.id).all()
    by_id = {p.id: p for p in rows}
    out: dict[str, list[ButtonPermBrief]] = {}
    for p in rows:
        if p.type != "button" or not p.parent_id:
            continue
        parent = by_id.get(p.parent_id)
        if not parent or parent.type != "menu":
            continue
        out.setdefault(parent.code, []).append(ButtonPermBrief(code=p.code, name=p.name))
    return out


def _menu_out(
    m: SysMenu,
    children: list[SysMenuOut] | None = None,
    btn_index: dict[str, list[ButtonPermBrief]] | None = None,
) -> SysMenuOut:
    return SysMenuOut(
        id=m.id,
        parent_id=m.parent_id,
        title=m.title,
        path=m.path,
        icon=m.icon,
        sort_order=m.sort_order,
        permission_code=m.permission_code,
        visible=m.visible,
        component=m.component,
        button_perms=(btn_index or {}).get(m.permission_code, []),
        children=children or [],
    )


def _build_perm_tree(rows: list[SysPermission]) -> list[PermTreeNode]:
    nodes = {
        p.id: PermTreeNode(
            id=p.id,
            code=p.code,
            name=p.name,
            type=p.type,
            parent_id=p.parent_id,
            sort_order=p.sort_order,
            children=[],
        )
        for p in rows
    }
    roots: list[PermTreeNode] = []
    for p in sorted(rows, key=lambda x: (x.sort_order, x.id)):
        node = nodes[p.id]
        if p.parent_id and p.parent_id in nodes:
            nodes[p.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


def _build_menu_tree(
    rows: list[SysMenu],
    allowed: set[str] | None,
    btn_index: dict[str, list[ButtonPermBrief]] | None = None,
) -> list[SysMenuOut]:
    children_map: dict[int | None, list[SysMenu]] = {}
    for m in rows:
        children_map.setdefault(m.parent_id, []).append(m)
    for k in children_map:
        children_map[k].sort(key=lambda x: (x.sort_order, x.id))

    def walk(parent_id: int | None) -> list[SysMenuOut]:
        out: list[SysMenuOut] = []
        for m in children_map.get(parent_id, []):
            if not m.visible:
                continue
            kids = walk(m.id)
            if allowed is not None and "*" not in allowed:
                has_self = m.permission_code in allowed
                if m.path:
                    if not has_self:
                        continue
                else:
                    if not has_self and not kids:
                        continue
            out.append(_menu_out(m, kids, btn_index))
        return out

    return walk(None)


# ---------- users ----------
@router.get("/users", response_model=list[SysUserOut])
def list_users(
    status: str | None = Query(default=None),
    position_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.sys.users")),
):
    q = db.query(SysUser).options(joinedload(SysUser.roles))
    if status:
        q = q.filter(SysUser.status == status)
    if position_id is not None:
        q = q.filter(SysUser.position_id == position_id)
    rows = q.order_by(SysUser.id).all()
    return [_user_out(db, u) for u in rows]


@router.post("/users", response_model=SysUserOut)
def create_user(
    body: SysUserCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.create")),
):
    if db.query(SysUser).filter(SysUser.username == body.username).first():
        raise HTTPException(400, detail="用户名已存在")
    if body.status not in ALLOWED_USER_STATUS:
        raise HTTPException(400, detail=f"非法状态: {body.status}")
    if body.position_id is not None and not db.get(Position, body.position_id):
        raise HTTPException(400, detail="岗位不存在")
    u = SysUser(
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        employee_id=body.employee_id,
        position_id=body.position_id,
        phone=body.phone,
        email=body.email,
        status=body.status,
    )
    db.add(u)
    db.flush()
    if body.employee_id is not None:
        bind_user_employee(db, u, body.employee_id)
    for rid in body.role_ids:
        db.add(SysUserRole(user_id=u.id, role_id=rid))
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == u.id).first()
    return _user_out(db, u)


@router.put("/users/{user_id}", response_model=SysUserOut)
def update_user(
    user_id: int,
    body: SysUserUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.edit")),
):
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    if not u:
        raise HTTPException(404, detail="用户不存在")
    if body.display_name is not None:
        u.display_name = body.display_name
    if body.password:
        u.password_hash = hash_password(body.password)
        revoke_user_tokens(db, u.id)
    data = body.model_dump(exclude_unset=True)
    if "employee_id" in data:
        bind_user_employee(db, u, data["employee_id"])
    if "position_id" in data:
        pid = data["position_id"]
        if pid is not None and not db.get(Position, pid):
            raise HTTPException(400, detail="岗位不存在")
        u.position_id = pid
    if "phone" in data:
        u.phone = data["phone"]
    if "email" in data:
        u.email = data["email"]
    if body.status is not None:
        if body.status not in ALLOWED_USER_STATUS:
            raise HTTPException(400, detail=f"非法状态: {body.status}")
        prev = u.status
        u.status = body.status
        if body.status in ("frozen", "disabled") and prev == "active":
            revoke_user_tokens(db, u.id)
    if body.role_ids is not None:
        db.query(SysUserRole).filter(SysUserRole.user_id == u.id).delete()
        for rid in body.role_ids:
            db.add(SysUserRole(user_id=u.id, role_id=rid))
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    return _user_out(db, u)


@router.post("/users/{user_id}/freeze", response_model=SysUserOut)
def freeze_user(
    user_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.edit")),
):
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    if not u:
        raise HTTPException(404, detail="用户不存在")
    u.status = "frozen"
    revoke_user_tokens(db, u.id)
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    return _user_out(db, u)


@router.post("/users/{user_id}/unfreeze", response_model=SysUserOut)
def unfreeze_user(
    user_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.edit")),
):
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    if not u:
        raise HTTPException(404, detail="用户不存在")
    u.status = "active"
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    return _user_out(db, u)


@router.post("/users/{user_id}/reset-password", response_model=SysUserOut)
def reset_password(
    user_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.edit")),
):
    password = (body or {}).get("password")
    if not password or len(str(password)) < 4:
        raise HTTPException(400, detail="新密码至少 4 位")
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    if not u:
        raise HTTPException(404, detail="用户不存在")
    u.password_hash = hash_password(str(password))
    revoke_user_tokens(db, u.id)
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    return _user_out(db, u)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.edit")),
):
    u = db.get(SysUser, user_id)
    if not u:
        raise HTTPException(404, detail="用户不存在")
    revoke_user_tokens(db, user_id)
    db.query(SysUserRole).filter(SysUserRole.user_id == user_id).delete()
    db.delete(u)
    db.commit()
    return {"message": "已删除"}


# ---------- roles ----------
@router.get("/roles", response_model=list[SysRoleOut])
def list_roles(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.sys.roles"))):
    rows = db.query(SysRole).options(joinedload(SysRole.permissions)).order_by(SysRole.id).all()
    return [_role_out(r) for r in rows]


@router.post("/roles", response_model=SysRoleOut)
def create_role(
    body: SysRoleCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.roles.edit")),
):
    if db.query(SysRole).filter(SysRole.code == body.code).first():
        raise HTTPException(400, detail="角色编码已存在")
    r = SysRole(code=body.code, name=body.name, description=body.description, status=body.status)
    db.add(r)
    db.flush()
    for pid in body.permission_ids:
        db.add(SysRolePermission(role_id=r.id, permission_id=pid))
    db.commit()
    r = db.query(SysRole).options(joinedload(SysRole.permissions)).filter(SysRole.id == r.id).first()
    return _role_out(r)


@router.put("/roles/{role_id}", response_model=SysRoleOut)
def update_role(
    role_id: int,
    body: SysRoleUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.roles.edit")),
):
    r = db.query(SysRole).options(joinedload(SysRole.permissions)).filter(SysRole.id == role_id).first()
    if not r:
        raise HTTPException(404, detail="角色不存在")
    if body.name is not None:
        r.name = body.name
    if body.description is not None:
        r.description = body.description
    if body.status is not None:
        r.status = body.status
    if body.permission_ids is not None:
        db.query(SysRolePermission).filter(SysRolePermission.role_id == r.id).delete()
        for pid in body.permission_ids:
            db.add(SysRolePermission(role_id=r.id, permission_id=pid))
    db.commit()
    r = db.query(SysRole).options(joinedload(SysRole.permissions)).filter(SysRole.id == role_id).first()
    return _role_out(r)


# ---------- permissions ----------
@router.get("/permissions", response_model=list[SysPermissionOut])
def list_permissions(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_user_or_api_key)):
    return db.query(SysPermission).order_by(SysPermission.sort_order, SysPermission.id).all()


@router.get("/permissions/tree", response_model=list[PermTreeNode])
def permissions_tree(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_user_or_api_key)):
    rows = db.query(SysPermission).order_by(SysPermission.sort_order, SysPermission.id).all()
    return _build_perm_tree(rows)


@router.post("/permissions", response_model=SysPermissionOut)
def create_permission(
    body: SysPermissionCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.sys.permissions")),
):
    if db.query(SysPermission).filter(SysPermission.code == body.code).first():
        raise HTTPException(400, detail="权限编码已存在")
    p = SysPermission(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------- menus (dynamic sidebar) ----------
@router.get("/menus/tree", response_model=list[SysMenuOut])
def menus_tree(db: Session = Depends(get_db), auth: AuthContext = Depends(require_user_or_api_key)):
    rows = db.query(SysMenu).order_by(SysMenu.sort_order, SysMenu.id).all()
    allowed = None if auth.is_api_key else auth.permission_codes
    # sidebar does not need button_perms payload; keep empty for light response
    return _build_menu_tree(rows, allowed, None)


@router.get("/menus", response_model=list[SysMenuOut])
def list_menus_admin(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.sys.menus"))):
    """Full menu tree for 菜单配置 (unfiltered) + linked button permission codes."""
    rows = db.query(SysMenu).order_by(SysMenu.sort_order, SysMenu.id).all()
    btn_index = _button_perms_index(db)
    return _build_menu_tree(rows, None, btn_index)


@router.post("/menus", response_model=SysMenuOut)
def create_menu(
    body: SysMenuCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.menus.edit")),
):
    m = SysMenu(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return _menu_out(m, None, _button_perms_index(db))


@router.put("/menus/{menu_id}", response_model=SysMenuOut)
def update_menu(
    menu_id: int,
    body: SysMenuUpdate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.menus.edit")),
):
    m = db.get(SysMenu, menu_id)
    if not m:
        raise HTTPException(404, detail="菜单不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _menu_out(m, None, _button_perms_index(db))


@router.delete("/menus/{menu_id}")
def delete_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.menus.edit")),
):
    m = db.get(SysMenu, menu_id)
    if not m:
        raise HTTPException(404, detail="菜单不存在")
    kids = db.query(SysMenu).filter(SysMenu.parent_id == menu_id).count()
    if kids:
        raise HTTPException(400, detail="请先删除子菜单")
    db.delete(m)
    db.commit()
    return {"message": "已删除"}
