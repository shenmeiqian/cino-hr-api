"""Auth: X-API-Key bypass + Bearer session tokens."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models.sys_rbac import SysPermission, SysRole, SysToken, SysUser

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split("$", 1)
    except ValueError:
        return False
    check = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return secrets.compare_digest(check, digest)


def create_token(db: Session, user_id: int, hours: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    row = SysToken(
        token=token,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=hours),
    )
    db.add(row)
    db.commit()
    return token


def revoke_token(db: Session, token: str) -> None:
    row = db.query(SysToken).filter(SysToken.token == token).first()
    if row:
        db.delete(row)
        db.commit()


def revoke_user_tokens(db: Session, user_id: int) -> int:
    """Invalidate all session tokens for a user (freeze / disable / reset password)."""
    n = db.query(SysToken).filter(SysToken.user_id == user_id).delete()
    db.flush()
    return n


def get_user_permissions(user: SysUser) -> list[SysPermission]:
    seen: dict[int, SysPermission] = {}
    for role in user.roles or []:
        if role.status != "active":
            continue
        for p in role.permissions or []:
            seen[p.id] = p
    return list(seen.values())


def load_user_with_rbac(db: Session, user_id: int) -> Optional[SysUser]:
    return (
        db.query(SysUser)
        .options(
            joinedload(SysUser.roles).joinedload(SysRole.permissions),
        )
        .filter(SysUser.id == user_id)
        .first()
    )


def user_login_blocked_message(status_value: str) -> str | None:
    if status_value == "active":
        return None
    if status_value == "frozen":
        return "账号已冻结，请联系管理员解冻后再登录"
    if status_value == "disabled":
        return "账号已禁用，无法登录"
    return f"账号状态异常（{status_value}），无法登录"


class AuthContext:
    """Authenticated caller: either API-key (super) or session user."""

    def __init__(
        self,
        *,
        is_api_key: bool = False,
        user: Optional[SysUser] = None,
        token: Optional[str] = None,
        permissions: Optional[list[SysPermission]] = None,
    ):
        self.is_api_key = is_api_key
        self.user = user
        self.token = token
        self.permissions = permissions or []

    @property
    def permission_codes(self) -> set[str]:
        if self.is_api_key:
            return {"*"}
        return {p.code for p in self.permissions}

    def has_perm(self, code: str) -> bool:
        if self.is_api_key:
            return True
        return code in self.permission_codes


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key，请在请求头提供正确的 X-API-Key",
        )
    return x_api_key


async def require_user_or_api_key(
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> AuthContext:
    settings = get_settings()
    if x_api_key and x_api_key == settings.api_key:
        return AuthContext(is_api_key=True)

    token = creds.credentials if creds else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录（Bearer token）或提供 X-API-Key",
        )
    row = db.query(SysToken).filter(SysToken.token == token).first()
    if not row or row.expires_at < datetime.utcnow():
        if row:
            db.delete(row)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    user = load_user_with_rbac(db, row.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    blocked = user_login_blocked_message(user.status)
    if blocked:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=blocked)
    perms = get_user_permissions(user)
    return AuthContext(is_api_key=False, user=user, token=token, permissions=perms)


def require_perm(code: str):
    async def _dep(auth: AuthContext = Depends(require_user_or_api_key)) -> AuthContext:
        if not auth.has_perm(code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无权限执行此操作（缺少权限码 {code}）")
        return auth

    return _dep
