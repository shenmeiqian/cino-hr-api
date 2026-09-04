"""Approval workflow definition designer & instances."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.schemas.workflow import (
    WorkflowAdvance,
    WorkflowDefinitionCreate,
    WorkflowDefinitionOut,
    WorkflowDefinitionUpdate,
    WorkflowInstanceCreate,
    WorkflowInstanceOut,
)

router = APIRouter(
    prefix="/api/v1/workflows", tags=["workflows"], dependencies=[Depends(require_api_key)]
)


def _parse_json(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


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
        nodes=_parse_json(row.nodes_json),
        edges=_parse_json(row.edges_json),
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
    nodes = _parse_json(row.nodes_json)
    if not nodes:
        raise HTTPException(400, detail="请先设计节点后再发布")
    row.status = "published"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/instances", response_model=list[WorkflowInstanceOut])
def list_instances(db: Session = Depends(get_db)):
    return db.query(WorkflowInstance).order_by(WorkflowInstance.id.desc()).all()


@router.post("/instances", response_model=WorkflowInstanceOut)
def start_instance(body: WorkflowInstanceCreate, db: Session = Depends(get_db)):
    defn = db.get(WorkflowDefinition, body.definition_id)
    if not defn:
        raise HTTPException(404, detail="流程定义不存在")
    if defn.status != "published":
        raise HTTPException(400, detail="仅已发布流程可启动实例")
    nodes = _parse_json(defn.nodes_json)
    start = next((n for n in nodes if n.get("type") == "start"), None)
    current = None
    if start:
        edges = _parse_json(defn.edges_json)
        nxt = next((e for e in edges if e.get("source") == start.get("id")), None)
        current = nxt.get("target") if nxt else start.get("id")
    row = WorkflowInstance(
        definition_id=body.definition_id,
        business_type=body.business_type,
        business_id=body.business_id,
        status="running",
        current_node_id=current,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/instances/{item_id}/advance", response_model=WorkflowInstanceOut)
def advance_instance(item_id: int, body: WorkflowAdvance, db: Session = Depends(get_db)):
    row = db.get(WorkflowInstance, item_id)
    if not row:
        raise HTTPException(404, detail="流程实例不存在")
    if row.status != "running":
        raise HTTPException(400, detail=f"实例状态为 {row.status}，无法推进")
    if body.action == "reject":
        row.status = "rejected"
        db.commit()
        db.refresh(row)
        return row
    if body.action != "approve":
        raise HTTPException(400, detail="action 须为 approve 或 reject")

    defn = db.get(WorkflowDefinition, row.definition_id)
    if not defn:
        raise HTTPException(404, detail="流程定义不存在")
    nodes = {n["id"]: n for n in _parse_json(defn.nodes_json) if "id" in n}
    edges = _parse_json(defn.edges_json)
    cur = row.current_node_id
    if not cur or cur not in nodes:
        row.status = "approved"
        db.commit()
        db.refresh(row)
        return row
    node = nodes[cur]
    if node.get("type") == "end":
        row.status = "approved"
        db.commit()
        db.refresh(row)
        return row
    nxt_edge = next((e for e in edges if e.get("source") == cur), None)
    if not nxt_edge:
        row.status = "approved"
        db.commit()
        db.refresh(row)
        return row
    nxt_id = nxt_edge.get("target")
    nxt = nodes.get(nxt_id) if nxt_id else None
    if not nxt or nxt.get("type") == "end":
        row.current_node_id = nxt_id
        row.status = "approved"
    else:
        row.current_node_id = nxt_id
    db.commit()
    db.refresh(row)
    return row
