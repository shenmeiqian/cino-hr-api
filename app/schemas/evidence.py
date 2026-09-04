from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class EvidenceCreate(BaseModel):
    ref_type: str
    ref_id: int
    employee_id: Optional[int] = None
    title: str
    file_url: Optional[str] = None
    content: Optional[str] = None
    uploaded_by: Optional[str] = None


class EvidenceUpdate(BaseModel):
    title: Optional[str] = None
    file_url: Optional[str] = None
    content: Optional[str] = None
    uploaded_by: Optional[str] = None
    employee_id: Optional[int] = None


class EvidenceOut(ORMModel):
    id: int
    ref_type: str
    ref_id: int
    employee_id: Optional[int] = None
    title: str
    file_url: Optional[str] = None
    content: Optional[str] = None
    uploaded_by: Optional[str] = None
    created_at: Optional[datetime] = None
