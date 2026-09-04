"""Login / me / logout / SSO."""
from __future__ import annotations

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    AuthContext,
    create_token,
    get_user_permissions,
    hash_password,
    load_user_with_rbac,
    require_user_or_api_key,
    revoke_token,
    verify_password,
)
from app.config import get_settings
from app.database import get_db
from app.models.sys_rbac import SysUser
from app.schemas.sys_rbac import LoginIn, LoginOut, MeOut, UserBrief

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# in-memory OIDC state store (demo)
_OIDC_STATES: dict[str, str] = {}


def _login_payload(db: Session, user: SysUser, token: str) -> LoginOut:
    user = load_user_with_rbac(db, user.id) or user
    perms = get_user_permissions(user)
    return LoginOut(
        token=token,
        user=UserBrief.model_validate(user),
        roles=[r.code for r in (user.roles or []) if r.status == "active"],
        permissions=[p.code for p in perms],
    )


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(SysUser).filter(SysUser.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, detail="用户名或密码错误")
    from app.auth import user_login_blocked_message
    from datetime import datetime

    blocked = user_login_blocked_message(user.status)
    if blocked:
        raise HTTPException(403, detail=blocked)
    user.last_login_at = datetime.utcnow()
    db.commit()
    token = create_token(db, user.id)
    return _login_payload(db, user, token)


@router.get("/me", response_model=MeOut)
def me(auth: AuthContext = Depends(require_user_or_api_key)):
    if auth.is_api_key:
        return MeOut(
            user=UserBrief(
                id=0, username="api-key", display_name="API Key", status="active"
            ),
            roles=["admin"],
            permissions=["*"],
            is_api_key=True,
        )
    assert auth.user
    return MeOut(
        user=UserBrief.model_validate(auth.user),
        roles=[r.code for r in (auth.user.roles or []) if r.status == "active"],
        permissions=sorted(auth.permission_codes),
        is_api_key=False,
    )


@router.post("/logout")
def logout(auth: AuthContext = Depends(require_user_or_api_key), db: Session = Depends(get_db)):
    if auth.token:
        revoke_token(db, auth.token)
    return {"message": "已退出"}


@router.get("/sso/status")
def sso_status():
    s = get_settings()
    configured = bool(s.oidc_issuer and s.oidc_client_id and s.oidc_client_secret)
    return {
        "configured": configured,
        "hint": None
        if configured
        else "请配置环境变量 OIDC_ISSUER / OIDC_CLIENT_ID / OIDC_CLIENT_SECRET / OIDC_REDIRECT_URI",
    }


@router.get("/sso/login")
def sso_login():
    s = get_settings()
    if not (s.oidc_issuer and s.oidc_client_id and s.oidc_client_secret):
        raise HTTPException(
            400,
            detail="SSO 未配置：需要 OIDC_ISSUER、OIDC_CLIENT_ID、OIDC_CLIENT_SECRET",
        )
    state = secrets.token_urlsafe(16)
    _OIDC_STATES[state] = "1"
    authorize = s.oidc_issuer.rstrip("/") + "/authorize"
    # common OIDC discovery fallback: if issuer has .well-known, callers should set issuer to auth server
    q = urlencode(
        {
            "response_type": "code",
            "client_id": s.oidc_client_id,
            "redirect_uri": s.oidc_redirect_uri,
            "scope": "openid profile email",
            "state": state,
        }
    )
    return RedirectResponse(f"{authorize}?{q}")


@router.get("/sso/callback")
async def sso_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    s = get_settings()
    if state not in _OIDC_STATES:
        raise HTTPException(400, detail="无效的 SSO state")
    _OIDC_STATES.pop(state, None)
    token_url = s.oidc_issuer.rstrip("/") + "/token"
    userinfo_url = s.oidc_issuer.rstrip("/") + "/userinfo"
    async with httpx.AsyncClient(timeout=20) as client:
        tok = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": s.oidc_redirect_uri,
                "client_id": s.oidc_client_id,
                "client_secret": s.oidc_client_secret,
            },
        )
        if tok.status_code >= 400:
            raise HTTPException(400, detail=f"SSO token 交换失败: {tok.text}")
        access = tok.json().get("access_token")
        ui = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access}"})
        if ui.status_code >= 400:
            raise HTTPException(400, detail=f"SSO userinfo 失败: {ui.text}")
        info = ui.json()
    email = info.get("email") or info.get("preferred_username") or info.get("sub")
    name = info.get("name") or email
    username = f"sso_{email}".replace("@", "_")[:60]
    user = db.query(SysUser).filter(SysUser.username == username).first()
    if not user:
        user = SysUser(
            username=username,
            display_name=name,
            password_hash=hash_password(secrets.token_urlsafe(12)),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_token(db, user.id)
    redirect = f"{s.oidc_frontend_redirect}?token={token}"
    return RedirectResponse(redirect)
