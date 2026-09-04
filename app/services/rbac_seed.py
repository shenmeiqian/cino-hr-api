"""Seed permissions (tree via parent_id), roles, users, and SysMenu tree."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models.employee import Employee
from app.models.sys_menu import SysMenu
from app.models.sys_rbac import SysPermission, SysRole, SysRolePermission, SysUser, SysUserRole

# (code, name, type, parent_code, sort) — parent resolved to parent_id after insert
PERM_TREE = [
    ("menu.workbench", "工作台", "menu", None, 10),
    ("menu.dashboard", "仪表盘", "menu", "menu.workbench", 11),
    ("menu.todos", "待办审批", "menu", "menu.workbench", 12),
    ("menu.principles", "原则说明", "menu", "menu.workbench", 13),
    ("menu.hr", "人事业务", "menu", None, 20),
    ("menu.employees", "员工花名册", "menu", "menu.hr", 21),
    ("btn.employees.create", "新建员工", "button", "menu.employees", 1),
    ("btn.employees.edit", "编辑员工", "button", "menu.employees", 2),
    ("api.employees.read", "员工只读API", "api", "menu.employees", 3),
    ("api.employees.write", "员工写API", "api", "menu.employees", 4),
    ("menu.org", "编制与岗位", "menu", "menu.hr", 22),
    ("api.org.read", "编制岗位只读", "api", "menu.org", 1),
    ("api.org.write", "编制岗位写API", "api", "menu.org", 2),
    ("menu.recruiting", "招聘入职闭环", "menu", "menu.hr", 23),
    ("btn.recruiting.create", "新建招聘", "button", "menu.recruiting", 1),
    ("btn.recruiting.submit", "提交审批", "button", "menu.recruiting", 2),
    ("api.recruiting.write", "招聘写API", "api", "menu.recruiting", 3),
    ("menu.onboarding", "入职单", "menu", "menu.hr", 24),
    ("btn.onboarding.create", "新建入职", "button", "menu.onboarding", 1),
    ("btn.onboarding.submit", "提交审批", "button", "menu.onboarding", 2),
    ("api.onboarding.write", "入职写API", "api", "menu.onboarding", 3),
    ("menu.contracts", "合同社保", "menu", "menu.hr", 25),
    ("btn.contracts.create", "登记合同", "button", "menu.contracts", 1),
    ("btn.contracts.submit", "提交审批", "button", "menu.contracts", 2),
    ("api.contracts.write", "合同写API", "api", "menu.contracts", 3),
    ("menu.trainings", "培训管理", "menu", "menu.hr", 26),
    ("btn.trainings.create", "新建培训", "button", "menu.trainings", 1),
    ("btn.trainings.pass", "登记通过", "button", "menu.trainings", 2),
    ("api.trainings.write", "培训写API", "api", "menu.trainings", 3),
    ("menu.attendance", "考勤异常", "menu", "menu.hr", 28),
    ("btn.attendance.create", "新建考勤异常", "button", "menu.attendance", 1),
    ("api.attendance.write", "考勤写API", "api", "menu.attendance", 2),
    ("menu.evidences", "R2/ISO证据", "menu", "menu.hr", 29),
    ("btn.evidences.create", "上传证据", "button", "menu.evidences", 1),
    ("api.evidences.write", "证据写API", "api", "menu.evidences", 2),
    ("menu.tickets", "人事工单", "menu", "menu.hr", 30),
    ("btn.tickets.create", "新建工单", "button", "menu.tickets", 1),
    ("btn.tickets.submit", "提交审批", "button", "menu.tickets", 2),
    ("api.tickets.write", "工单写API", "api", "menu.tickets", 3),
    ("menu.emergency", "紧急用工", "menu", "menu.hr", 31),
    ("btn.emergency.create", "发起紧急用工", "button", "menu.emergency", 1),
    ("btn.emergency.submit", "提交审批", "button", "menu.emergency", 2),
    ("api.emergency.write", "紧急用工写API", "api", "menu.emergency", 3),
    ("menu.kpi", "KPI 跑批", "menu", "menu.hr", 32),
    ("btn.kpi.run", "跑批 KPI", "button", "menu.kpi", 1),
    ("api.kpi.run", "KPI跑批API", "api", "menu.kpi", 2),
    ("menu.approval", "审批中心", "menu", None, 40),
    ("menu.workflows", "审批流设计", "menu", "menu.approval", 41),
    ("btn.workflows.create", "新建流程", "button", "menu.workflows", 1),
    ("btn.workflows.save", "保存流程", "button", "menu.workflows", 2),
    ("btn.workflows.publish", "发布流程", "button", "menu.workflows", 3),
    ("btn.workflows.start", "启动实例", "button", "menu.workflows", 4),
    ("btn.workflows.advance", "审批推进", "button", "menu.todos", 1),
    ("api.workflows.write", "流程写API", "api", "menu.workflows", 5),
    ("menu.files", "文件管理", "menu", "menu.approval", 42),
    ("btn.files.upload", "上传文件", "button", "menu.files", 1),
    ("btn.files.delete", "删除文件", "button", "menu.files", 2),
    ("api.files.write", "文件写API", "api", "menu.files", 3),
    ("menu.notifications", "通知日志", "menu", "menu.approval", 43),
    ("btn.notifications.send", "发送通知", "button", "menu.notifications", 1),
    ("api.notifications.send", "通知发送API", "api", "menu.notifications", 2),
    ("menu.sys", "系统管理", "menu", None, 90),
    ("menu.sys.users", "用户管理", "menu", "menu.sys", 91),
    ("btn.sys.users.create", "新建用户", "button", "menu.sys.users", 1),
    ("btn.sys.users.edit", "编辑用户", "button", "menu.sys.users", 2),
    ("api.sys.users.write", "用户写API", "api", "menu.sys.users", 3),
    ("menu.sys.roles", "角色管理", "menu", "menu.sys", 92),
    ("btn.sys.roles.edit", "编辑角色", "button", "menu.sys.roles", 1),
    ("api.sys.roles.write", "角色写API", "api", "menu.sys.roles", 2),
    ("menu.sys.permissions", "权限目录", "menu", "menu.sys", 93),
    ("menu.sys.menus", "菜单配置", "menu", "menu.sys", 94),
    ("btn.sys.menus.edit", "编辑菜单", "button", "menu.sys.menus", 1),
    ("api.sys.menus.write", "菜单写API", "api", "menu.sys.menus", 2),
    ("menu.permissions", "开权审计日志", "menu", "menu.sys", 95),
    ("btn.permissions.grant", "开权", "button", "menu.permissions", 1),
    ("btn.permissions.revoke", "停权", "button", "menu.permissions", 2),
    ("api.permissions.write", "开权写API", "api", "menu.permissions", 3),
]

# (title, path, permission_code, parent_permission_code, sort, icon)
MENU_SEED = [
    ("工作台", None, "menu.workbench", None, 10, "home"),
    ("仪表盘", "/", "menu.dashboard", "menu.workbench", 11, None),
    ("待办审批", "/todos", "menu.todos", "menu.workbench", 12, None),
    ("原则说明", "/principles", "menu.principles", "menu.workbench", 13, None),
    ("人事业务", None, "menu.hr", None, 20, "users"),
    ("员工花名册", "/employees", "menu.employees", "menu.hr", 21, None),
    ("编制与岗位", "/org", "menu.org", "menu.hr", 22, None),
    ("招聘入职闭环", "/recruiting", "menu.recruiting", "menu.hr", 23, None),
    ("入职单", "/onboarding", "menu.onboarding", "menu.hr", 24, None),
    ("合同社保", "/contracts", "menu.contracts", "menu.hr", 25, None),
    ("培训管理", "/trainings", "menu.trainings", "menu.hr", 26, None),
    ("考勤异常", "/attendance", "menu.attendance", "menu.hr", 28, None),
    ("R2/ISO证据", "/evidences", "menu.evidences", "menu.hr", 29, None),
    ("人事工单", "/tickets", "menu.tickets", "menu.hr", 30, None),
    ("紧急用工", "/emergency", "menu.emergency", "menu.hr", 31, None),
    ("KPI 跑批", "/kpi", "menu.kpi", "menu.hr", 32, None),
    ("审批中心", None, "menu.approval", None, 40, "flow"),
    ("审批流设计", "/workflows", "menu.workflows", "menu.approval", 41, None),
    ("文件管理", "/files", "menu.files", "menu.approval", 42, None),
    ("通知日志", "/notifications", "menu.notifications", "menu.approval", 43, None),
    ("系统管理", None, "menu.sys", None, 90, "settings"),
    ("用户管理", "/sys/users", "menu.sys.users", "menu.sys", 91, None),
    ("角色管理", "/sys/roles", "menu.sys.roles", "menu.sys", 92, None),
    ("权限目录", "/sys/permissions", "menu.sys.permissions", "menu.sys", 93, None),
    ("菜单配置", "/sys/menus", "menu.sys.menus", "menu.sys", 94, None),
    ("开权审计日志", "/permissions", "menu.permissions", "menu.sys", 95, None),
]


def ensure_permissions(db: Session) -> dict[str, SysPermission]:
    by_code: dict[str, SysPermission] = {p.code: p for p in db.query(SysPermission).all()}
    # insert parents before children (PERM_TREE is already parent-before-child)
    for code, name, typ, parent_code, sort in PERM_TREE:
        parent_id = by_code[parent_code].id if parent_code and parent_code in by_code else None
        if code in by_code:
            row = by_code[code]
            row.name = name
            row.type = typ
            row.parent_id = parent_id
            row.sort_order = sort
            continue
        p = SysPermission(code=code, name=name, type=typ, parent_id=parent_id, sort_order=sort)
        db.add(p)
        db.flush()
        by_code[code] = p
        # re-resolve in case parent was just created earlier in loop
    # second pass: fix parent_id for any that were created before parent existed (shouldn't happen)
    for code, name, typ, parent_code, sort in PERM_TREE:
        if parent_code and code in by_code and parent_code in by_code:
            by_code[code].parent_id = by_code[parent_code].id
    db.flush()
    return by_code


def ensure_menus(db: Session) -> None:
    if db.query(SysMenu).count() > 0:
        return
    code_to_id: dict[str, int] = {}
    for title, path, perm_code, parent_perm, sort, icon in MENU_SEED:
        parent_id = code_to_id.get(parent_perm) if parent_perm else None
        m = SysMenu(
            parent_id=parent_id,
            title=title,
            path=path,
            icon=icon,
            sort_order=sort,
            permission_code=perm_code,
            visible=True,
        )
        db.add(m)
        db.flush()
        code_to_id[perm_code] = m.id
    db.flush()


def _set_role_perms(db: Session, role: SysRole, codes: list[str], by_code: dict[str, SysPermission]):
    db.query(SysRolePermission).filter(SysRolePermission.role_id == role.id).delete()
    for c in codes:
        p = by_code.get(c)
        if p:
            db.add(SysRolePermission(role_id=role.id, permission_id=p.id))


def seed_rbac(db: Session) -> None:
    by_code = ensure_permissions(db)
    ensure_menus(db)
    all_codes = list(by_code.keys())

    def get_or_create_role(code: str, name: str, desc: str) -> SysRole:
        r = db.query(SysRole).filter(SysRole.code == code).first()
        if not r:
            r = SysRole(code=code, name=name, description=desc, status="active")
            db.add(r)
            db.flush()
        return r

    admin = get_or_create_role("admin", "系统管理员", "全部权限")
    hr = get_or_create_role("hr", "人事专员", "人事业务权限（无系统管理）")
    viewer = get_or_create_role("viewer", "只读访客", "仅菜单只读")

    _set_role_perms(db, admin, all_codes, by_code)

    hr_codes = [
        c
        for c in all_codes
        if not c.startswith("menu.sys")
        and not c.startswith("btn.sys")
        and not c.startswith("api.sys")
        and not c.startswith("menu.permissions")
        and not c.startswith("btn.permissions")
        and not c.startswith("api.permissions")
        and c not in ("menu.notifications", "btn.notifications.send", "api.notifications.send")
    ]
    for g in ("menu.workbench", "menu.hr", "menu.approval"):
        if g in by_code and g not in hr_codes:
            hr_codes.append(g)
    _set_role_perms(db, hr, hr_codes, by_code)

    viewer_codes = [
        c
        for c in all_codes
        if c.startswith("menu.")
        and not c.startswith("menu.sys")
        and not c.startswith("menu.permissions")
        and c != "menu.notifications"
    ]
    _set_role_perms(db, viewer, viewer_codes, by_code)

    from app.models.position import Position

    def _pos_id(code: str | None) -> int | None:
        if not code:
            return None
        row = db.query(Position).filter(Position.code == code).first()
        return row.id if row else None

    def ensure_user(
        username: str,
        password: str,
        display: str,
        role: SysRole,
        emp_no: str | None,
        position_code: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ):
        u = db.query(SysUser).filter(SysUser.username == username).first()
        emp_id = None
        if emp_no:
            emp = db.query(Employee).filter(Employee.emp_no == emp_no).first()
            emp_id = emp.id if emp else None
        pos_id = _pos_id(position_code)
        if not u:
            u = SysUser(
                username=username,
                display_name=display,
                password_hash=hash_password(password),
                employee_id=emp_id,
                position_id=pos_id,
                phone=phone,
                email=email,
                status="active",
            )
            db.add(u)
            db.flush()
        else:
            # keep password stable for demos; refresh display/status/basics
            u.display_name = display
            u.status = "active"
            if emp_id and not u.employee_id:
                u.employee_id = emp_id
            if pos_id and not getattr(u, "position_id", None):
                u.position_id = pos_id
            if phone and not getattr(u, "phone", None):
                u.phone = phone
            if email and not getattr(u, "email", None):
                u.email = email
        # replace roles to single demo role
        db.query(SysUserRole).filter(SysUserRole.user_id == u.id).delete()
        db.add(SysUserRole(user_id=u.id, role_id=role.id))

    ensure_user("admin", "admin123", "系统管理员", admin, "E2001", "HR-MANAGER", "13800000001", "admin@cino.local")
    ensure_user("hr", "hr123", "王人事", hr, "E2001", "HR-MANAGER", "13800000002", "hr@cino.local")
    ensure_user("viewer", "viewer123", "只读访客", viewer, "E1002", "MEDIA-CONTACT", None, "viewer@cino.local")
    db.commit()
    print("Seed RBAC+Menus: admin/hr/viewer + permission tree(parent_id) + SysMenu")
