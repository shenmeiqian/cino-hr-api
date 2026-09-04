"""File management API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.file_object import FileObject
from app.schemas.common import ORMModel
from app.services.file_storage import delete_file, read_bytes, save_upload
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class FileOut(ORMModel):
    id: int
    filename: str
    content_type: Optional[str] = None
    size: int
    storage_backend: str
    storage_key: str
    sha256: Optional[str] = None
    uploaded_by: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    created_at: Optional[datetime] = None


@router.get("", response_model=list[FileOut])
def list_files(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.files")),
    ref_type: str | None = None,
    ref_id: int | None = None,
):
    q = db.query(FileObject)
    if ref_type:
        q = q.filter(FileObject.ref_type == ref_type)
    if ref_id is not None:
        q = q.filter(FileObject.ref_id == ref_id)
    return q.order_by(FileObject.id.desc()).all()


@router.post("/upload", response_model=FileOut)
async def upload_file(
    file: UploadFile = File(...),
    ref_type: str | None = Form(default=None),
    ref_id: int | None = Form(default=None),
    backend: str | None = Form(default=None, description="Override: local|s3|database"),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_perm("btn.files.upload")),
):
    uploader = "api-key" if auth.is_api_key else (auth.user.username if auth.user else None)
    return await save_upload(
        db, file, uploaded_by=uploader, ref_type=ref_type, ref_id=ref_id, backend=backend
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("menu.files")),
):
    obj = db.get(FileObject, file_id)
    if not obj:
        raise HTTPException(404, detail="文件不存在")
    data = read_bytes(db, obj)
    return Response(
        content=data,
        media_type=obj.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{obj.filename}"'},
    )


@router.delete("/{file_id}")
def remove_file(
    file_id: int,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.files.delete")),
):
    obj = db.get(FileObject, file_id)
    if not obj:
        raise HTTPException(404, detail="文件不存在")
    delete_file(db, obj)
    return {"message": "已删除"}
