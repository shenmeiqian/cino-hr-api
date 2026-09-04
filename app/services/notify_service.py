"""Multi-channel notification service."""
from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.notification import NotificationLog


def send_notification(
    db: Session,
    *,
    channel: str,
    to: str,
    title: str,
    body: str = "",
    ref_type: str | None = None,
    ref_id: int | None = None,
) -> NotificationLog:
    channel = channel.lower()
    status = "dry_run"
    error: Optional[str] = None
    try:
        if channel == "email":
            status, error = _send_email(to, title, body)
        elif channel == "sms":
            status, error = _send_sms(to, title, body)
        elif channel == "wecom":
            status, error = _send_webhook(get_settings().wecom_webhook_url, title, body, to)
        elif channel == "dingtalk":
            status, error = _send_webhook(get_settings().dingtalk_webhook_url, title, body, to)
        elif channel == "feishu":
            status, error = _send_feishu(get_settings().feishu_webhook_url, title, body)
        else:
            status, error = "failed", f"未知渠道: {channel}"
    except Exception as e:  # noqa: BLE001
        status, error = "failed", str(e)

    log = NotificationLog(
        channel=channel,
        to_addr=to,
        title=title,
        body=body,
        status=status,
        error=error,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _send_email(to: str, title: str, body: str) -> tuple[str, Optional[str]]:
    s = get_settings()
    if not s.smtp_host:
        return "dry_run", "SMTP 未配置，已记录为 dry-run"
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
    return "sent", None


def _send_sms(to: str, title: str, body: str) -> tuple[str, Optional[str]]:
    s = get_settings()
    if s.sms_provider == "aliyun" and s.aliyun_sms_access_key:
        return "dry_run", "Aliyun SMS 接口未完整实现，已 dry-run"
    if s.sms_provider == "tencent" and s.tencent_sms_secret_id:
        return "dry_run", "Tencent SMS 接口未完整实现，已 dry-run"
    return "dry_run", f"demo SMS provider: to={to} title={title} body={body[:80]}"


def _send_webhook(url: str, title: str, body: str, to: str) -> tuple[str, Optional[str]]:
    if not url:
        return "dry_run", "Webhook URL 未配置"
    payload = {"msgtype": "text", "text": {"content": f"{title}\n{body}\n@{to}"}}
    r = httpx.post(url, json=payload, timeout=15)
    if r.status_code >= 400:
        return "failed", r.text
    return "sent", None


def _send_feishu(url: str, title: str, body: str) -> tuple[str, Optional[str]]:
    if not url:
        return "dry_run", "飞书 Webhook 未配置"
    payload = {
        "msg_type": "text",
        "content": {"text": f"{title}\n{body}"},
    }
    r = httpx.post(url, json=payload, timeout=15)
    if r.status_code >= 400:
        return "failed", r.text
    return "sent", None


def notify_workflow_event(db: Session, inst, event: str) -> None:
    """Best-effort notify on workflow advance/complete."""
    title = f"审批流{event}: {inst.business_type}#{inst.business_id}"
    body = f"实例 #{inst.id} 状态={inst.status} 当前节点={inst.current_node_id}"
    # email dry-run to placeholder
    send_notification(
        db,
        channel="email",
        to="approver@cino.demo",
        title=title,
        body=body,
        ref_type="workflow_instance",
        ref_id=inst.id,
    )
    s = get_settings()
    if s.wecom_webhook_url:
        send_notification(
            db,
            channel="wecom",
            to="workflow",
            title=title,
            body=body,
            ref_type="workflow_instance",
            ref_id=inst.id,
        )
