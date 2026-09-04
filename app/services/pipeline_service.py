"""入职业务闭环 + 自动开权评估."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.headcount import HeadcountPlan
from app.models.onboarding import Onboarding
from app.models.permission import PermissionEvent
from app.models.recruiting import RecruitingReq
from app.models.training import Training
from app.services import workflow_service as wfs

STAGES = [
    ("headcount", "批准编制"),
    ("open", "提招聘需求"),
    ("candidate", "录用/候选人"),
    ("approval", "提交审批流"),
    ("onboarding", "生成入职单"),
    ("contract", "合同社保"),
    ("training", "培训有效期"),
    ("grant", "开权评估"),
    ("closed", "闭环完成"),
]

MEDIA_COURSES = ("safety", "sop", "wipe_r2")


def grant_status_for_employee(db: Session, emp: Employee | None) -> str:
    if not emp:
        return "n/a"
    granted = (
        db.query(PermissionEvent)
        .filter(
            PermissionEvent.employee_id == emp.id,
            PermissionEvent.event_type == "grant",
            PermissionEvent.status.in_(["done", "completed", "success", "granted"]),
        )
        .first()
    )
    if granted:
        return "granted"
    # training gate for media contact
    if emp.is_media_contact:
        today = date.today()
        ok = True
        for code in MEDIA_COURSES:
            t = (
                db.query(Training)
                .filter(
                    Training.employee_id == emp.id,
                    Training.course_code == code,
                    Training.status == "passed",
                )
                .order_by(Training.id.desc())
                .first()
            )
            if not t or (t.valid_until and t.valid_until < today):
                ok = False
                break
        if not ok:
            return "pending_train"
        return "ready"
    # non-media: ready if any training or always ready
    return "ready"


def auto_grant_if_ready(db: Session, emp: Employee, operator: str = "system-auto") -> PermissionEvent | None:
    status = grant_status_for_employee(db, emp)
    if status != "ready":
        return None
    scopes = "wipe,outbound" if emp.is_media_contact else "basic_erp"
    ev = PermissionEvent(
        employee_id=emp.id,
        event_type="grant",
        scopes=scopes,
        reason="入职闭环自动开权（培训闸门通过）",
        trigger="hire_pipeline",
        status="done",
        completed_at=datetime.utcnow(),
        operator=operator,
    )
    db.add(ev)
    db.flush()
    return ev


def build_timeline(db: Session, row: RecruitingReq) -> list[dict[str, Any]]:
    emp = db.get(Employee, row.employee_id) if row.employee_id else None
    gstat = grant_status_for_employee(db, emp)
    stage_order = [s[0] for s in STAGES]
    cur_idx = stage_order.index(row.stage) if row.stage in stage_order else 0
    out = []
    for i, (key, label) in enumerate(STAGES):
        state = "done" if i < cur_idx or row.status == "closed" else ("current" if i == cur_idx else "pending")
        if key == "grant":
            extra = gstat
        elif key == "approval":
            inst = wfs.instance_for_business(db, "recruiting", row.id)
            extra = inst.status if inst else "未提交"
        else:
            extra = None
        out.append({"key": key, "label": label, "state": state, "extra": extra})
    return out


def enrich(db: Session, row: RecruitingReq) -> dict[str, Any]:
    emp = db.get(Employee, row.employee_id) if row.employee_id else None
    return {
        "grant_status": grant_status_for_employee(db, emp),
        "timeline": build_timeline(db, row),
    }


def check_headcount(db: Session, row: RecruitingReq) -> None:
    if not row.position_id:
        raise HTTPException(400, detail="请先指定岗位")
    ym = date.today().strftime("%Y-%m")
    plan = (
        db.query(HeadcountPlan)
        .filter(
            HeadcountPlan.position_id == row.position_id,
            HeadcountPlan.year_month == ym,
            HeadcountPlan.status == "approved",
        )
        .first()
    )
    if not plan:
        # fallback any approved plan for position
        plan = (
            db.query(HeadcountPlan)
            .filter(HeadcountPlan.position_id == row.position_id, HeadcountPlan.status == "approved")
            .order_by(HeadcountPlan.id.desc())
            .first()
        )
    if not plan or plan.vacancy <= 0:
        raise HTTPException(400, detail="无可用空编（编制未批准或 vacancy=0）")
    row.stage = "open"
    row.status = "headcount_ok"


def advance(db: Session, row: RecruitingReq, action: str, payload: dict, actor: str = "system") -> RecruitingReq:
    if action == "check_headcount":
        check_headcount(db, row)
    elif action == "open_req":
        if row.stage not in ("open", "headcount"):
            raise HTTPException(400, detail="请先完成编制检查")
        if row.stage == "headcount":
            check_headcount(db, row)
        row.status = "open"
        row.stage = "candidate"
        row.open_date = row.open_date or date.today()
    elif action == "set_candidate":
        name = payload.get("candidate_name")
        if not name:
            raise HTTPException(400, detail="请填写候选人姓名")
        row.candidate_name = name
        row.candidate_phone = payload.get("candidate_phone")
        if payload.get("employee_id"):
            row.employee_id = payload["employee_id"]
        row.stage = "approval"
        row.status = "candidate"
    elif action == "submit_approval":
        if row.stage not in ("approval", "candidate"):
            raise HTTPException(400, detail="请先登记候选人")
        wfs.start_instance(db, business_type="recruiting", business_id=row.id)
        row.stage = "approval"
        row.status = "in_approval"
    elif action == "gen_onboarding":
        # only after approved
        inst = wfs.instance_for_business(db, "recruiting", row.id)
        if not inst or inst.status != "approved":
            raise HTTPException(400, detail="审批流未通过，无法生成入职单")
        if not row.employee_id:
            # create employee from candidate
            emp = Employee(
                emp_no=f"E{date.today().strftime('%y%m')}{row.id:03d}",
                name=row.candidate_name or f"候选人{row.id}",
                dept_id=row.dept_id,
                position_id=row.position_id,
                status="active",
                hire_date=date.today(),
                phone=row.candidate_phone,
            )
            db.add(emp)
            db.flush()
            row.employee_id = emp.id
        ob = Onboarding(
            employee_id=row.employee_id,
            plan_start=date.today(),
            checklist_status="pending",
            account_bound=False,
            remark=f"由招聘需求 {row.req_no} 自动生成",
        )
        db.add(ob)
        db.flush()
        row.onboarding_id = ob.id
        row.stage = "contract"
        row.status = "onboarding"
    elif action == "gen_contract":
        if not row.employee_id:
            raise HTTPException(400, detail="无关联员工")
        if row.stage not in ("contract", "onboarding"):
            raise HTTPException(400, detail="请先完成入职单阶段")
        ct = Contract(
            employee_id=row.employee_id,
            contract_no=f"CT-{row.req_no}",
            contract_type="fixed",
            start_date=date.today(),
            status="active",
            remark=f"闭环自动生成 {row.req_no}",
        )
        db.add(ct)
        db.flush()
        row.contract_id = ct.id
        row.stage = "training"
        row.status = "contract"
    elif action == "eval_grant":
        if not row.employee_id:
            raise HTTPException(400, detail="无关联员工")
        emp = db.get(Employee, row.employee_id)
        assert emp
        # move past training
        row.stage = "grant"
        ev = auto_grant_if_ready(db, emp, operator=actor)
        g = grant_status_for_employee(db, emp)
        if g == "granted" or ev:
            row.stage = "closed"
            row.status = "closed"
            row.close_date = date.today()
        elif g == "pending_train":
            row.status = "trained"  # waiting
            row.stage = "training"
        else:
            row.status = "grant_ready"
            row.stage = "grant"
    else:
        raise HTTPException(400, detail=f"未知 action: {action}")
    db.commit()
    db.refresh(row)
    return row


def sync_grant_on_workflow_approved(db: Session, business_type: str, business_id: int) -> None:
    """When recruiting approved, bump stage; when onboarding approved, try auto grant if linked."""
    if business_type == "recruiting":
        row = db.get(RecruitingReq, business_id)
        if row and row.status == "in_approval":
            row.status = "approved"
            row.stage = "onboarding"
            db.flush()
    elif business_type == "onboarding":
        ob = db.get(Onboarding, business_id)
        if ob:
            emp = db.get(Employee, ob.employee_id)
            if emp:
                auto_grant_if_ready(db, emp)
