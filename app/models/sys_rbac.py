"""Local RBAC: users, roles, permissions (tree), tokens."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SysUser(Base):
    __tablename__ = "sys_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)
    position_id: Mapped[Optional[int]] = mapped_column(ForeignKey("positions.id"), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # active | frozen | disabled
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    roles: Mapped[list["SysRole"]] = relationship(
        secondary="sys_user_roles", back_populates="users"
    )


class SysRole(Base):
    __tablename__ = "sys_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")

    users: Mapped[list["SysUser"]] = relationship(
        secondary="sys_user_roles", back_populates="roles"
    )
    permissions: Mapped[list["SysPermission"]] = relationship(
        secondary="sys_role_permissions", back_populates="roles"
    )


class SysPermission(Base):
    __tablename__ = "sys_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # menu|button|api
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sys_permissions.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    roles: Mapped[list["SysRole"]] = relationship(
        secondary="sys_role_permissions", back_populates="permissions"
    )


class SysUserRole(Base):
    __tablename__ = "sys_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_users.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("sys_roles.id"), nullable=False)


class SysRolePermission(Base):
    __tablename__ = "sys_role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("sys_roles.id"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("sys_permissions.id"), nullable=False)


class SysToken(Base):
    __tablename__ = "sys_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
