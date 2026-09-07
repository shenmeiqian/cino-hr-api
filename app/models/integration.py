"""综合系统 3.0 对接配置与同步日志（无真实凭证）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IntegrationConfig(Base):
    """演示用对接配置。禁止存放综合系统 3.0 真实密钥。"""

    __tablename__ = "integration_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # RFC 2606 .invalid — 占位地址，不可作为真实环境
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(32), default="api_key")  # api_key / none
    # 仅说明文字，例如 “由 3.0 调用本服务时使用 X-API-Key”
    credential_hint: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="demo")  # demo/disabled
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IntegrationSyncLog(Base):
    """同步批次日志，供 GET /sync/status 展示最近同步时间与数量。"""

    __tablename__ = "integration_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False)  # users / permissions / full
    status: Mapped[str] = mapped_column(String(32), default="success")  # success/partial/failed
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    count_in: Mapped[int] = mapped_column(Integer, default=0)
    count_created: Mapped[int] = mapped_column(Integer, default=0)
    count_updated: Mapped[int] = mapped_column(Integer, default=0)
    count_linked: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
