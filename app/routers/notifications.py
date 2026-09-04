"""Notification send + logs."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm
from app.database import get_db
from app.models.notification import NotificationLog
from app.schemas.common import ORMModel
from app.services.notify_service import send_notification

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotifySendIn(BaseModel):
    channel: str
    to: str
    title: str
    body: str = ""


class NotifyOut(ORMModel):
    id: int
    channel: str
    to_addr: str
    title: str
    body: Optional[str] = None
    status: str
    error: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    created_at: Optional[datetime] = None


@router.get("", response_model=list[NotifyOut])
def list_logs(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.notifications")),
):
    return db.query(NotificationLog).order_by(NotificationLog.id.desc()).limit(200).all()


@router.post("/send", response_model=NotifyOut)
def send(
    body: NotifySendIn,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.notifications.send")),
):
    return send_notification(
        db, channel=body.channel, to=body.to, title=body.title, body=body.body
    )
