"""Approval workflow definition designer & instances."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_user_or_api_key
from app.database import get_db
from app.models.workflow import WorkflowDefinition, WorkflowHistory, WorkflowInstance
from app.schemas.sys_rbac import WorkflowSubmitIn, WorkflowTodoOut
from app.schemas.workflow import (
    WorkflowAdvance,
    WorkflowDefinitionCreate,
    WorkflowDefinitionOut,
    WorkflowDefinitionUpdate,
    WorkflowHistoryOut,
    WorkflowInstanceCreate,
    WorkflowInstanceDetailOut,
    WorkflowInstanceOut,
)
from app.services import workflow_service as wfs
from app.services.notify_service import notify_workflow_event

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["workflows"],
    dependencies=[Depends(require_user_or_api_key)],
)


def _to_out(row: WorkflowDefinition) -> WorkflowDefinitionOut:
    return WorkflowDefinitionOut(
        id=row.id,
        code=row.code,
        name=row.name,
        description=row.description,
        status=row.status,
        nodes_json=row.nodes_json or "[]",
        edges_json=row.edges_json or "[]",
        created_at=row.created_at,
        updated_at=row.updated_at,
        nodes=wfs.parse_json(row.nodes_json),
        edges=wfs.parse_json(row.edges_json),
    )


@router.get("/definitions", response_model=list[WorkflowDefinitionOut])
def list_definitions(db: Session = Depends(get_db)):
    rows = db.query(WorkflowDefinition).order_by(WorkflowDefinition.id.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("/definitions", response_model=WorkflowDefinitionOut)
def create_definition(body: WorkflowDefinitionCreate, db: Session = Depends(get_db)):
    if db.query(WorkflowDefinition).filter(WorkflowDefinition.code == body.code).first():
        raise HTTPException(400, detail=f"流程编码已存在: {body.code}")
    nodes = body.nodes or []
    edges = body.edges or []
    row = WorkflowDefinition(
        code=body.code,
        name=body.name,
        description=body.description,
        status="draft",
        nodes_json=json.dumps(nodes, ensure_ascii=False),
        edges_json=json.dumps(edges, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/definitions/{item_id}", response_model=WorkflowDefinitionOut)
def get_definition(item_id: int, db: Session = Depends(get_db)):
    row = db.get(WorkflowDefinition, item_id)
    if not row:
        raise HTTPException(404, detail="流程定义不存在")
    return _to_out(row)


@router.put("/definitions/{item_id}", response_model=WorkflowDefinitionOut)
def update_definition(
    item_id: int, body: WorkflowDefinitionUpdate, db: Session = Depends(get_db)
):
    row = db.get(WorkflowDefinition, item_id)
    if not row:
        raise HTTPException(404, detail="流程定义不存在")
    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    if body.status is not None:
        row.status = body.status
    if body.nodes is not None:
        row.nodes_json = json.dumps(body.nodes, ensure_ascii=False)
    if body.edges is not None:
        row.edges_json = json.dumps(body.edges, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/definitions/{item_id}/publish", response_model=WorkflowDefinitionOut)
def publish_definition(item_id: int, db: Session = Depends(get_db)):
    row = db.get(WorkflowDefinition, item_id)
    if not row:
        raise HTTPException(404, detail="流程定义不存在")
    nodes = wfs.parse_json(row.nodes_json)
    if not nodes:
        raise HTTPException(400, detail="请先设计节点后再发布")
    row.status = "published"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/instances", response_model=list[WorkflowInstanceOut])
def list_instances(
    db: Session = Depends(get_db),
    business_type: str | None = None,
    business_id: int | None = None,
):
    q = db.query(WorkflowInstance)
    if business_type:
        q = q.filter(WorkflowInstance.business_type == business_type)
    if business_id is not None:
        q = q.filter(WorkflowInstance.business_id == business_id)
    return q.order_by(WorkflowInstance.id.desc()).all()


@router.post("/instances", response_model=WorkflowInstanceOut)
def start_instance(body: WorkflowInstanceCreate, db: Session = Depends(get_db)):
    return wfs.start_instance(
        db,
        business_type=body.business_type,
        business_id=body.business_id,
        definition_id=body.definition_id,
    )


@router.post("/submit", response_model=WorkflowInstanceOut)
def submit_document(
    body: WorkflowSubmitIn,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_user_or_api_key),
):
    """单据提交审批：按 business_type 绑定已发布流程并启动实例。"""
    row = wfs.start_instance(
        db,
        business_type=body.business_type,
        business_id=body.business_id,
        definition_id=body.definition_id,
        definition_code=body.definition_code,
    )
    actor = "api-key" if auth.is_api_key else (auth.user.username if auth.user else "user")
    db.add(
        WorkflowHistory(
            instance_id=row.id,
            node_id=row.current_node_id,
            node_label="提交审批",
            action="submit",
            actor=actor,
            comment="单据提交审批流",
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/todos", response_model=list[WorkflowTodoOut])
def my_todos(db: Session = Depends(get_db), auth: AuthContext = Depends(require_user_or_api_key)):
    emp_id = None if auth.is_api_key else (auth.user.employee_id if auth.user else None)
    # admin / api-key sees all running; others filtered by position code
    is_admin = auth.is_api_key or ("admin" in [r.code for r in (auth.user.roles or [])])
    items = wfs.list_todos_for_user(db, emp_id, is_api_key=is_admin)
    return items


def _load_business(db: Session, business_type: str, business_id: int):
    from app.models.recruiting import RecruitingReq
    from app.models.onboarding import Onboarding
    from app.models.contract import Contract
    from app.models.emergency import EmergencyApproval
    from app.models.ticket import Ticket
    from app.services.pipeline_service import enrich

    mapping = {
        "recruiting": RecruitingReq,
        "onboarding": Onboarding,
        "contracts": Contract,
        "emergency": EmergencyApproval,
        "tickets": Ticket,
    }
    model = mapping.get(business_type)
    if not model:
        return {"error": f"未知业务类型: {business_type}"}
    row = db.get(model, business_id)
    if not row:
        return {"error": f"业务单据不存在: {business_type}#{business_id}"}
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    for k, v in list(data.items()):
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
    if business_type == "recruiting":
        data.update(enrich(db, row))
    return data


@router.get("/instances/{item_id}", response_model=WorkflowInstanceDetailOut)
def get_instance_detail(item_id: int, db: Session = Depends(get_db)):
    row = db.get(WorkflowInstance, item_id)
    if not row:
        raise HTTPException(404, detail="流程实例不存在")
    defn = db.get(WorkflowDefinition, row.definition_id)
    meta = wfs.current_node_meta(defn, row.current_node_id)
    hist = (
        db.query(WorkflowHistory)
        .filter(WorkflowHistory.instance_id == item_id)
        .order_by(WorkflowHistory.id.asc())
        .all()
    )
    return WorkflowInstanceDetailOut(
        id=row.id,
        definition_id=row.definition_id,
        business_type=row.business_type,
        business_id=row.business_id,
        status=row.status,
        current_node_id=row.current_node_id,
        created_at=row.created_at,
        definition_code=defn.code if defn else None,
        definition_name=defn.name if defn else None,
        current_node_label=meta.get("current_node_label"),
        approver_role=meta.get("approver_role"),
        history=[WorkflowHistoryOut.model_validate(h) for h in hist],
        business=_load_business(db, row.business_type, row.business_id),
    )


@router.post("/instances/{item_id}/advance", response_model=WorkflowInstanceOut)
def advance_instance(
    item_id: int,
    body: WorkflowAdvance,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_user_or_api_key),
):
    before = db.get(WorkflowInstance, item_id)
    if not before:
        raise HTTPException(404, detail="流程实例不存在")
    defn = db.get(WorkflowDefinition, before.definition_id)
    meta = wfs.current_node_meta(defn, before.current_node_id)
    actor = "api-key" if auth.is_api_key else (auth.user.username if auth.user else "user")
    row = wfs.advance_instance(db, item_id, body.action)
    db.add(
        WorkflowHistory(
            instance_id=item_id,
            node_id=before.current_node_id,
            node_label=meta.get("current_node_label"),
            action=body.action,
            actor=actor,
            comment=body.comment,
        )
    )
    db.commit()
    try:
        notify_workflow_event(db, row, "推进" if body.action == "approve" else "驳回")
    except Exception:
        pass
    return row
