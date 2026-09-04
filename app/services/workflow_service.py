"""Workflow helpers: start, advance, sync document status, todos."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.emergency import EmergencyApproval
from app.models.employee import Employee
from app.models.onboarding import Onboarding
from app.models.position import Position
from app.models.recruiting import RecruitingReq
from app.models.ticket import Ticket
from app.models.workflow import WorkflowDefinition, WorkflowInstance

BUSINESS_DEF_CODES = {
    "onboarding": "ONBOARD-APPROVAL",
    "recruiting": "RECRUIT-APPROVAL",
    "contracts": "CONTRACT-APPROVAL",
    "emergency": "EMERGENCY-APPROVAL",
    "tickets": "TICKET-APPROVAL",
}


def parse_json(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []



def validate_approver_roles(db: Session, nodes: list) -> None:
    """Approval nodes must use a real local Position.code as approverRole (no free text)."""
    codes = {c for (c,) in db.query(Position.code).all()}
    bad = []
    for n in nodes or []:
        if n.get("type") != "approval":
            continue
        role = (n.get("approverRole") or "").strip()
        if not role:
            bad.append(f"{n.get('id')}: 审批节点缺少 approverRole（须选本地岗位 code）")
        elif role not in codes:
            bad.append(f"{n.get('id')}: approverRole={role} 不是有效岗位编码")
    if bad:
        raise HTTPException(400, detail="审批岗位校验失败: " + "; ".join(bad))

def find_start_current(defn: WorkflowDefinition) -> Optional[str]:
    nodes = parse_json(defn.nodes_json)
    edges = parse_json(defn.edges_json)
    start = next((n for n in nodes if n.get("type") == "start"), None)
    if not start:
        return None
    nxt = next((e for e in edges if e.get("source") == start.get("id")), None)
    return nxt.get("target") if nxt else start.get("id")


def resolve_definition(
    db: Session,
    *,
    definition_id: int | None = None,
    definition_code: str | None = None,
    business_type: str | None = None,
) -> WorkflowDefinition:
    defn = None
    if definition_id:
        defn = db.get(WorkflowDefinition, definition_id)
    elif definition_code:
        defn = db.query(WorkflowDefinition).filter(WorkflowDefinition.code == definition_code).first()
    elif business_type:
        code = BUSINESS_DEF_CODES.get(business_type)
        if code:
            defn = db.query(WorkflowDefinition).filter(WorkflowDefinition.code == code).first()
        if not defn:
            defn = (
                db.query(WorkflowDefinition)
                .filter(
                    WorkflowDefinition.status == "published",
                    WorkflowDefinition.code.ilike(f"%{business_type}%"),
                )
                .first()
            )
    if not defn:
        raise HTTPException(404, detail="未找到匹配的已发布审批流定义")
    if defn.status != "published":
        raise HTTPException(400, detail="仅已发布流程可启动实例")
    return defn


def start_instance(
    db: Session,
    *,
    business_type: str,
    business_id: int,
    definition_id: int | None = None,
    definition_code: str | None = None,
) -> WorkflowInstance:
    existing = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.business_type == business_type,
            WorkflowInstance.business_id == business_id,
            WorkflowInstance.status == "running",
        )
        .first()
    )
    if existing:
        raise HTTPException(400, detail=f"单据已有进行中的审批实例 #{existing.id}")

    defn = resolve_definition(
        db,
        definition_id=definition_id,
        definition_code=definition_code,
        business_type=business_type,
    )
    # mark document as in_approval if applicable
    _mark_document_submitted(db, business_type, business_id)

    row = WorkflowInstance(
        definition_id=defn.id,
        business_type=business_type,
        business_id=business_id,
        status="running",
        current_node_id=find_start_current(defn),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mark_document_submitted(db: Session, business_type: str, business_id: int) -> None:
    if business_type == "onboarding":
        row = db.get(Onboarding, business_id)
        if row and row.checklist_status == "pending":
            row.checklist_status = "in_progress"
    elif business_type == "recruiting":
        row = db.get(RecruitingReq, business_id)
        if row and row.status == "open":
            row.status = "in_approval"
    elif business_type == "contracts":
        row = db.get(Contract, business_id)
        if row and row.status in ("draft", "pending", "active"):
            if row.status != "active":
                row.status = "in_approval"
            else:
                row.status = "terminate_pending"
    elif business_type == "emergency":
        row = db.get(EmergencyApproval, business_id)
        if row and row.status == "pending":
            row.status = "in_approval"
    elif business_type == "tickets":
        row = db.get(Ticket, business_id)
        if row and row.status == "open":
            row.status = "in_approval"
    db.flush()


def apply_document_result(db: Session, inst: WorkflowInstance) -> None:
    bt, bid, st = inst.business_type, inst.business_id, inst.status
    if bt == "onboarding":
        row = db.get(Onboarding, bid)
        if not row:
            return
        if st == "approved":
            row.checklist_status = "done"
            row.account_bound = True
            if not row.actual_start:
                row.actual_start = date.today()
        elif st == "rejected":
            row.checklist_status = "rejected"
    elif bt == "recruiting":
        row = db.get(RecruitingReq, bid)
        if not row:
            return
        if st == "approved":
            row.status = "closed"
            row.close_date = date.today()
        elif st == "rejected":
            row.status = "rejected"
    elif bt == "contracts":
        row = db.get(Contract, bid)
        if not row:
            return
        if st == "approved":
            if row.status == "terminate_pending":
                row.status = "terminated"
            else:
                row.status = "active"
        elif st == "rejected":
            row.status = "rejected"
    elif bt == "emergency":
        row = db.get(EmergencyApproval, bid)
        if not row:
            return
        if st == "approved":
            row.status = "approved"
            row.decided_at = datetime.utcnow()
            row.approver = row.approver or "workflow"
        elif st == "rejected":
            row.status = "rejected"
            row.decided_at = datetime.utcnow()
    elif bt == "tickets":
        row = db.get(Ticket, bid)
        if not row:
            return
        if st == "approved":
            row.status = "closed"
        elif st == "rejected":
            row.status = "rejected"
    db.flush()
    if st in ("approved", "rejected"):
        try:
            from app.services.pipeline_service import sync_grant_on_workflow_approved
            if st == "approved":
                sync_grant_on_workflow_approved(db, bt, bid)
        except Exception:
            pass


def advance_instance(db: Session, item_id: int, action: str) -> WorkflowInstance:
    row = db.get(WorkflowInstance, item_id)
    if not row:
        raise HTTPException(404, detail="流程实例不存在")
    if row.status != "running":
        raise HTTPException(400, detail=f"实例状态为 {row.status}，无法推进")
    if action == "reject":
        row.status = "rejected"
        apply_document_result(db, row)
        db.commit()
        db.refresh(row)
        return row
    if action != "approve":
        raise HTTPException(400, detail="action 须为 approve 或 reject")

    defn = db.get(WorkflowDefinition, row.definition_id)
    if not defn:
        raise HTTPException(404, detail="流程定义不存在")
    nodes = {n["id"]: n for n in parse_json(defn.nodes_json) if "id" in n}
    edges = parse_json(defn.edges_json)
    cur = row.current_node_id
    if not cur or cur not in nodes:
        row.status = "approved"
        apply_document_result(db, row)
        db.commit()
        db.refresh(row)
        return row
    node = nodes[cur]
    if node.get("type") == "end":
        row.status = "approved"
        apply_document_result(db, row)
        db.commit()
        db.refresh(row)
        return row
    nxt_edge = next((e for e in edges if e.get("source") == cur), None)
    if not nxt_edge:
        row.status = "approved"
        apply_document_result(db, row)
        db.commit()
        db.refresh(row)
        return row
    nxt_id = nxt_edge.get("target")
    nxt = nodes.get(nxt_id) if nxt_id else None
    if not nxt or nxt.get("type") == "end":
        row.current_node_id = nxt_id
        row.status = "approved"
        apply_document_result(db, row)
    else:
        row.current_node_id = nxt_id
    db.commit()
    db.refresh(row)
    return row


def current_node_meta(defn: WorkflowDefinition | None, node_id: str | None) -> dict[str, Any]:
    if not defn or not node_id:
        return {}
    nodes = {n["id"]: n for n in parse_json(defn.nodes_json) if "id" in n}
    n = nodes.get(node_id) or {}
    return {
        "current_node_label": n.get("label"),
        "approver_role": n.get("approverRole"),
    }


def list_todos_for_user(
    db: Session,
    user_employee_id: int | None,
    is_api_key: bool = False,
    user_position_id: int | None = None,
) -> list[dict]:
    q = db.query(WorkflowInstance).filter(WorkflowInstance.status == "running")
    rows = q.order_by(WorkflowInstance.id.desc()).all()
    pos_code = None
    if not is_api_key:
        pid = user_position_id
        if not pid and user_employee_id:
            emp = db.get(Employee, user_employee_id)
            if emp:
                pid = emp.position_id
        if pid:
            pos = db.get(Position, pid)
            pos_code = pos.code if pos else None

    out = []
    for r in rows:
        defn = db.get(WorkflowDefinition, r.definition_id)
        meta = current_node_meta(defn, r.current_node_id)
        role = meta.get("approver_role")
        if not is_api_key and pos_code and role and role != pos_code:
            continue
        if not is_api_key and not pos_code and not is_api_key:
            # no position bound → show none unless api key; still show all for admin convenience if no emp
            pass
        out.append(
            {
                "id": r.id,
                "definition_id": r.definition_id,
                "definition_code": defn.code if defn else None,
                "definition_name": defn.name if defn else None,
                "business_type": r.business_type,
                "business_id": r.business_id,
                "status": r.status,
                "current_node_id": r.current_node_id,
                "current_node_label": meta.get("current_node_label"),
                "approver_role": role,
                "created_at": r.created_at,
            }
        )
    return out


def instance_for_business(db: Session, business_type: str, business_id: int) -> WorkflowInstance | None:
    return (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.business_type == business_type,
            WorkflowInstance.business_id == business_id,
        )
        .order_by(WorkflowInstance.id.desc())
        .first()
    )
