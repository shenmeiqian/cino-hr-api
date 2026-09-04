"""File management models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FileObject(Base):
    __tablename__ = "file_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0)
    storage_backend: Mapped[str] = mapped_column(String(32), default="local")  # local|s3|database
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ref_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FileBlob(Base):
    __tablename__ = "file_blobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
