from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class WorkflowDefinitionCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    nodes: Optional[list[dict[str, Any]]] = None
    edges: Optional[list[dict[str, Any]]] = None


class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list[dict[str, Any]]] = None
    edges: Optional[list[dict[str, Any]]] = None
    status: Optional[str] = None


class WorkflowDefinitionOut(ORMModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    status: str
    nodes_json: str
    edges_json: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowInstanceCreate(BaseModel):
    definition_id: int
    business_type: str
    business_id: int


class WorkflowAdvance(BaseModel):
    action: str  # approve|reject
    comment: Optional[str] = None


class WorkflowInstanceOut(ORMModel):
    id: int
    definition_id: int
    business_type: str
    business_id: int
    status: str
    current_node_id: Optional[str] = None
    created_at: Optional[datetime] = None


class WorkflowHistoryOut(ORMModel):
    id: int
    instance_id: int
    node_id: Optional[str] = None
    node_label: Optional[str] = None
    action: str
    actor: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class WorkflowInstanceDetailOut(WorkflowInstanceOut):
    definition_code: Optional[str] = None
    definition_name: Optional[str] = None
    current_node_label: Optional[str] = None
    approver_role: Optional[str] = None
    history: list[WorkflowHistoryOut] = Field(default_factory=list)
    business: Optional[dict[str, Any]] = None
