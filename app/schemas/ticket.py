from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TicketCreate(BaseModel):
    ticket_no: str
    category: str = "general"
    title: str
    description: Optional[str] = None
    requester_emp_id: Optional[int] = None
    assignee_emp_id: Optional[int] = None
    status: str = "open"
    priority: str = "medium"


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    assignee_emp_id: Optional[int] = None
    priority: Optional[str] = None
    description: Optional[str] = None


class TicketOut(ORMModel):
    id: int
    ticket_no: str
    category: str
    title: str
    description: Optional[str] = None
    requester_emp_id: Optional[int] = None
    assignee_emp_id: Optional[int] = None
    status: str
    priority: str
    created_at: Optional[datetime] = None
