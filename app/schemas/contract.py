from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ContractCreate(BaseModel):
    employee_id: int
    contract_no: str
    contract_type: str = "fixed"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "active"
    file_url: Optional[str] = None
    remark: Optional[str] = None


class ContractUpdate(BaseModel):
    contract_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    file_url: Optional[str] = None
    remark: Optional[str] = None


class ContractOut(ORMModel):
    id: int
    employee_id: int
    contract_no: str
    contract_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    file_url: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
