"""File storage backends: local / s3 / database."""
from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.file_object import FileBlob, FileObject


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def save_upload(
    db: Session,
    file: UploadFile,
    *,
    uploaded_by: str | None = None,
    ref_type: str | None = None,
    ref_id: int | None = None,
    backend: str | None = None,
) -> FileObject:
    settings = get_settings()
    backend = (backend or settings.file_storage_backend or "local").lower()
    raw = await file.read()
    key = f"{uuid.uuid4().hex}_{file.filename}"
    if backend == "local":
        root = Path(settings.file_local_dir)
        root.mkdir(parents=True, exist_ok=True)
        path = root / key
        path.write_bytes(raw)
        storage_key = str(path)
    elif backend == "database":
        storage_key = key
        db.add(FileBlob(storage_key=key, content=raw))
    elif backend == "s3":
        if not (settings.s3_endpoint and settings.s3_bucket and settings.s3_access_key):
            raise HTTPException(400, detail="S3 未配置：需要 S3_ENDPOINT/S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY")
        try:
            import boto3
        except ImportError as e:
            raise HTTPException(500, detail="未安装 boto3，无法使用 S3 存储") from e
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=raw,
            ContentType=file.content_type or "application/octet-stream",
        )
        storage_key = key
    else:
        raise HTTPException(400, detail=f"未知存储后端: {backend}")

    obj = FileObject(
        filename=file.filename or key,
        content_type=file.content_type,
        size=len(raw),
        storage_backend=backend,
        storage_key=storage_key,
        sha256=_sha256(raw),
        uploaded_by=uploaded_by,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def read_bytes(db: Session, obj: FileObject) -> bytes:
    if obj.storage_backend == "local":
        return Path(obj.storage_key).read_bytes()
    if obj.storage_backend == "database":
        blob = db.query(FileBlob).filter(FileBlob.storage_key == obj.storage_key).first()
        if not blob:
            raise HTTPException(404, detail="文件内容不存在")
        return blob.content
    if obj.storage_backend == "s3":
        settings = get_settings()
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        resp = client.get_object(Bucket=settings.s3_bucket, Key=obj.storage_key)
        return resp["Body"].read()
    raise HTTPException(400, detail=f"未知存储后端: {obj.storage_backend}")


def delete_file(db: Session, obj: FileObject) -> None:
    if obj.storage_backend == "local":
        try:
            os.remove(obj.storage_key)
        except FileNotFoundError:
            pass
    elif obj.storage_backend == "database":
        db.query(FileBlob).filter(FileBlob.storage_key == obj.storage_key).delete()
    elif obj.storage_backend == "s3":
        settings = get_settings()
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        client.delete_object(Bucket=settings.s3_bucket, Key=obj.storage_key)
    db.delete(obj)
    db.commit()
