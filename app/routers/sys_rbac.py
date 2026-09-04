"""Admin CRUD: users / roles / permissions tree / dynamic menus."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth import AuthContext, hash_password, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.sys_menu import SysMenu
from app.models.sys_rbac import (
    SysPermission,
    SysRole,
    SysRolePermission,
    SysUser,
    SysUserRole,
)
from app.schemas.sys_rbac import (
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


def _user_out(u: SysUser) -> SysUserOut:
    roles = u.roles or []
    return SysUserOut(
        id=u.id,
        username=u.username,
        display_name=u.display_name,
        employee_id=u.employee_id,
        status=u.status,
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


def _menu_out(m: SysMenu, children: list[SysMenuOut] | None = None) -> SysMenuOut:
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


def _build_menu_tree(rows: list[SysMenu], allowed: set[str] | None) -> list[SysMenuOut]:
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
                    # leaf/page: must have own perm
                    if not has_self:
                        continue
                else:
                    # group: show if self perm OR any visible kids
                    if not has_self and not kids:
                        continue
            out.append(_menu_out(m, kids))
        return out

    return walk(None)


# ---------- users ----------
@router.get("/users", response_model=list[SysUserOut])
def list_users(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.sys.users"))):
    rows = db.query(SysUser).options(joinedload(SysUser.roles)).order_by(SysUser.id).all()
    return [_user_out(u) for u in rows]


@router.post("/users", response_model=SysUserOut)
def create_user(
    body: SysUserCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.create")),
):
    if db.query(SysUser).filter(SysUser.username == body.username).first():
        raise HTTPException(400, detail="用户名已存在")
    u = SysUser(
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        employee_id=body.employee_id,
        status=body.status,
    )
    db.add(u)
    db.flush()
    for rid in body.role_ids:
        db.add(SysUserRole(user_id=u.id, role_id=rid))
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == u.id).first()
    return _user_out(u)


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
    if body.employee_id is not None:
        u.employee_id = body.employee_id
    if body.status is not None:
        u.status = body.status
    if body.role_ids is not None:
        db.query(SysUserRole).filter(SysUserRole.user_id == u.id).delete()
        for rid in body.role_ids:
            db.add(SysUserRole(user_id=u.id, role_id=rid))
    db.commit()
    u = db.query(SysUser).options(joinedload(SysUser.roles)).filter(SysUser.id == user_id).first()
    return _user_out(u)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.sys.users.edit")),
):
    u = db.get(SysUser, user_id)
    if not u:
        raise HTTPException(404, detail="用户不存在")
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
        # replace full permission set
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
    return _build_menu_tree(rows, allowed)


@router.get("/menus", response_model=list[SysMenuOut])
def list_menus_admin(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.sys.menus"))):
    """Full menu tree for 菜单配置 (unfiltered)."""
    rows = db.query(SysMenu).order_by(SysMenu.sort_order, SysMenu.id).all()
    return _build_menu_tree(rows, None)


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
    return _menu_out(m)


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
    return _menu_out(m)


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
