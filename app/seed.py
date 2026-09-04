"""Seed demo data for CINO HR MVP."""
from datetime import date, timedelta
import json

from app.database import SessionLocal, init_db
from app.models.employee import Department, Employee
from app.models.headcount import HeadcountPlan
from app.models.position import Position, PositionClause, PositionRole
from app.models.notification import AppSetting
from app.models.sys_rbac import SysRole, SysUser
from app.models.training import Training
from app.models.workflow import WorkflowDefinition
from app.services.kpi_service import ensure_default_mappings
from app.services.rbac_seed import seed_rbac


def _approval_flow(code: str, name: str, description: str, role1: str, role2: str) -> dict:
    nodes = [
        {"id": "n-start", "type": "start", "label": "开始", "x": 80, "y": 160},
        {
            "id": "n-hr",
            "type": "approval",
            "label": "人事初审",
            "x": 280,
            "y": 160,
            "approverRole": role1,
        },
        {
            "id": "n-mgr",
            "type": "approval",
            "label": "岗位复核",
            "x": 480,
            "y": 160,
            "approverRole": role2,
        },
        {"id": "n-end", "type": "end", "label": "结束", "x": 680, "y": 160},
    ]
    edges = [
        {"id": "e1", "source": "n-start", "target": "n-hr"},
        {"id": "e2", "source": "n-hr", "target": "n-mgr"},
        {"id": "e3", "source": "n-mgr", "target": "n-end"},
    ]
    return {
        "code": code,
        "name": name,
        "description": description,
        "nodes": nodes,
        "edges": edges,
    }


def seed_workflows(db) -> None:
    """Ensure published approval flows bound to local position codes."""
    defs = [
        _approval_flow(
            "ONBOARD-APPROVAL",
            "入职审批",
            "入职审批流：开始 → 人事主管 → 媒体联络人 → 结束",
            "HR-MANAGER",
            "MEDIA-CONTACT",
        ),
        _approval_flow(
            "RECRUIT-APPROVAL",
            "招聘需求审批",
            "招聘审批：人事主管 → 媒体联络人",
            "HR-MANAGER",
            "MEDIA-CONTACT",
        ),
        _approval_flow(
            "CONTRACT-APPROVAL",
            "合同审批",
            "合同审批：人事主管 → 媒体联络人",
            "HR-MANAGER",
            "MEDIA-CONTACT",
        ),
        _approval_flow(
            "EMERGENCY-APPROVAL",
            "紧急用工审批",
            "紧急用工：人事主管 → 媒体联络人",
            "HR-MANAGER",
            "MEDIA-CONTACT",
        ),
        _approval_flow(
            "TICKET-APPROVAL",
            "工单审批",
            "人事工单：人事主管 → 媒体联络人",
            "HR-MANAGER",
            "MEDIA-CONTACT",
        ),
    ]
    for d in defs:
        row = db.query(WorkflowDefinition).filter(WorkflowDefinition.code == d["code"]).first()
        payload_nodes = json.dumps(d["nodes"], ensure_ascii=False)
        payload_edges = json.dumps(d["edges"], ensure_ascii=False)
        if not row:
            db.add(
                WorkflowDefinition(
                    code=d["code"],
                    name=d["name"],
                    description=d["description"],
                    status="published",
                    nodes_json=payload_nodes,
                    edges_json=payload_edges,
                )
            )
            print(f"Seed workflow: {d['name']} ({d['code']})")
        else:
            # refresh position-bound roles
            row.name = d["name"]
            row.description = d["description"]
            row.status = "published"
            row.nodes_json = payload_nodes
            row.edges_json = payload_edges
    db.commit()



def seed_position_roles(db) -> None:
    """Demo: HR-MANAGER → hr role; MEDIA-CONTACT → viewer role (position→role sync)."""
    mapping = {"HR-MANAGER": "hr", "MEDIA-CONTACT": "viewer", "TEMP-UNIVERSAL": "viewer"}
    for pos_code, role_code in mapping.items():
        pos = db.query(Position).filter(Position.code == pos_code).first()
        role = db.query(SysRole).filter(SysRole.code == role_code).first()
        if not pos or not role:
            continue
        exists = (
            db.query(PositionRole)
            .filter(PositionRole.position_id == pos.id, PositionRole.role_id == role.id)
            .first()
        )
        if not exists:
            db.add(PositionRole(position_id=pos.id, role_id=role.id))
            print(f"Seed PositionRole: {pos_code} → {role_code}")
    # sync_roles_from_position setting
    row = db.query(AppSetting).filter(AppSetting.key == "sync_roles_from_position").first()
    if not row:
        db.add(AppSetting(key="sync_roles_from_position", value="true"))
    # bidirectional employee ↔ user
    for u in db.query(SysUser).filter(SysUser.employee_id.isnot(None)).all():
        emp = db.query(Employee).filter(Employee.id == u.employee_id).first()
        if emp and emp.sys_user_id != u.id:
            emp.sys_user_id = u.id
    db.commit()


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Department).filter(Department.code == "HR").first():
            print("Seed data already exists, skip core.")
            ensure_default_mappings(db)
            seed_workflows(db)
            seed_rbac(db)
            seed_position_roles(db)
            return

        hr = Department(code="HR", name="人事行政部")
        ops = Department(code="OPS", name="回收运营部")
        db.add_all([hr, ops])
        db.flush()

        temp_pos = Position(
            code="TEMP-UNIVERSAL",
            title="通用临时岗",
            dept_id=ops.id,
            level="T0",
            is_universal_temp=True,
            jd_summary="适用于短期/外包/实习生的通用职责说明书",
            status="active",
        )
        media_pos = Position(
            code="MEDIA-CONTACT",
            title="媒体联络人",
            dept_id=hr.id,
            level="P2",
            is_universal_temp=False,
            jd_summary="对外媒体联络与设备擦除对外协调",
            status="active",
        )
        hr_mgr = Position(
            code="HR-MANAGER",
            title="人事主管",
            dept_id=hr.id,
            level="M1",
            jd_summary="人事主管 KPI 责任岗位",
            status="active",
        )
        db.add_all([temp_pos, media_pos, hr_mgr])
        db.flush()

        db.add_all(
            [
                PositionClause(
                    position_id=temp_pos.id,
                    clause_code="TEMP-01",
                    clause_title="服从现场安全规范",
                    content="进入作业区须佩戴防护并完成安全培训。",
                    weight=40,
                    sort_order=1,
                ),
                PositionClause(
                    position_id=media_pos.id,
                    clause_code="MEDIA-01",
                    clause_title="对外信息发布授权",
                    content="须完成 safety/sop/wipe_r2 培训后方可申请 wipe/outbound 权限。",
                    weight=50,
                    sort_order=1,
                ),
            ]
        )

        emp_media = Employee(
            emp_no="E1001",
            name="张媒体",
            dept_id=hr.id,
            position_id=media_pos.id,
            system_account_id="sys3-media-1001",
            status="active",
            hire_date=date(2024, 1, 15),
            is_media_contact=True,
            is_critical_role=True,
            phone="13800001001",
            email="media@cino.demo",
        )
        emp_trained = Employee(
            emp_no="E1002",
            name="李已训",
            dept_id=hr.id,
            position_id=media_pos.id,
            system_account_id="sys3-media-1002",
            status="active",
            hire_date=date(2024, 3, 1),
            is_media_contact=True,
            is_critical_role=False,
            phone="13800001002",
            email="trained@cino.demo",
        )
        emp_hr = Employee(
            emp_no="E2001",
            name="王人事",
            dept_id=hr.id,
            position_id=hr_mgr.id,
            system_account_id="sys3-hr-2001",
            status="active",
            hire_date=date(2023, 6, 1),
            is_media_contact=False,
            is_critical_role=True,
            phone="13800002001",
            email="hr@cino.demo",
        )
        emp_temp = Employee(
            emp_no="E3001",
            name="赵临时",
            dept_id=ops.id,
            position_id=temp_pos.id,
            system_account_id="sys3-temp-3001",
            status="active",
            hire_date=date.today() - timedelta(days=10),
            is_media_contact=False,
            is_critical_role=False,
        )
        db.add_all([emp_media, emp_trained, emp_hr, emp_temp])
        db.flush()

        today = date.today()
        valid = today + timedelta(days=180)
        for code, name in [
            ("safety", "安全培训"),
            ("sop", "SOP 操作规范"),
            ("wipe_r2", "设备擦除 R2 规范"),
        ]:
            db.add(
                Training(
                    employee_id=emp_trained.id,
                    course_code=code,
                    course_name=name,
                    status="passed",
                    score=95,
                    trained_at=today - timedelta(days=30),
                    valid_until=valid,
                )
            )

        db.add(
            HeadcountPlan(
                year_month=today.strftime("%Y-%m"),
                dept_id=hr.id,
                position_id=media_pos.id,
                planned_count=3,
                actual_count=2,
                vacancy=1,
                status="approved",
            )
        )
        db.add(
            HeadcountPlan(
                year_month=today.strftime("%Y-%m"),
                dept_id=ops.id,
                position_id=temp_pos.id,
                planned_count=5,
                actual_count=4,
                vacancy=1,
                status="approved",
            )
        )

        ensure_default_mappings(db)
        db.commit()
        print("Seed OK:")
        print(f"  departments: HR({hr.id}), OPS({ops.id})")
        print(f"  positions: TEMP({temp_pos.id}), MEDIA({media_pos.id}), HR-MGR({hr_mgr.id})")
        print(f"  employees: E1001(no train id={emp_media.id}), E1002(trained id={emp_trained.id})")
        seed_workflows(db)
        seed_rbac(db)
        seed_position_roles(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
