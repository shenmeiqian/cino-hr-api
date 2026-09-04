from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.emergency import EmergencyApproval
from app.models.ticket import Ticket
from app.schemas.emergency import EmergencyCreate, EmergencyOut, EmergencyUpdate
from app.schemas.ticket import TicketCreate, TicketOut, TicketUpdate

router = APIRouter(prefix="/api/v1", tags=["T12-T13-p1"], dependencies=[Depends(require_user_or_api_key)])


@router.post("/tickets", response_model=TicketOut)
def create_ticket(body: TicketCreate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("btn.tickets.create"))):
    row = Ticket(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.tickets"))):
    return db.query(Ticket).all()


@router.get("/tickets/{item_id}", response_model=TicketOut)
def get_ticket(item_id: int, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.tickets"))):
    row = db.get(Ticket, item_id)
    if not row:
        raise HTTPException(404, detail="工单不存在")
    return row


@router.patch("/tickets/{item_id}", response_model=TicketOut)
def update_ticket(item_id: int, body: TicketUpdate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("api.tickets.write"))):
    row = db.get(Ticket, item_id)
    if not row:
        raise HTTPException(404, detail="工单不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.post("/emergency-approvals", response_model=EmergencyOut)
def create_emergency(body: EmergencyCreate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("btn.emergency.create"))):
    row = EmergencyApproval(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/emergency-approvals", response_model=list[EmergencyOut])
def list_emergency(db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("menu.emergency"))):
    return db.query(EmergencyApproval).all()


@router.patch("/emergency-approvals/{item_id}", response_model=EmergencyOut)
def update_emergency(item_id: int, body: EmergencyUpdate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("api.emergency.write"))):
    row = db.get(EmergencyApproval, item_id)
    if not row:
        raise HTTPException(404, detail="紧急审批不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    if body.status in ("approved", "rejected"):
        row.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
