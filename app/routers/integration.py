from fastapi import APIRouter, Depends

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.schemas.integration import (
    PermissionCallbackIn,
    PendingRevokeOut,
    SyncStatusOut,
    SyncUsersIn,
    SyncUsersOut,
    ValidateTrainingIn,
    ValidateTrainingOut,
)
from app.schemas.permission import PermissionEventOut
from app.services.integration_service import (
    apply_permission_callback,
    list_pending_revokes,
    sync_status,
    sync_users,
    validate_training_before_grant,
)
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/api/v1/integration",
    tags=["综合系统3.0-integration"],
    dependencies=[Depends(require_user_or_api_key)],
)


@router.get(
    "/sync/status",
    response_model=SyncStatusOut,
    summary="同步状态",
    description=(
        "返回演示对接配置（不含真实凭证）、各 sync_type 最近一次同步时间与数量，"
        "以及当前 SysUser / 员工账号绑定 / T+0 待回收计数。"
        "Web 管理端用于展示 HR↔综合系统3.0 对接健康度。"
    ),
)
def get_sync_status(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.integration.read")),
):
    return sync_status(db)


@router.post(
    "/sync/users",
    response_model=SyncUsersOut,
    summary="同步 3.0 用户",
    description=(
        "接收综合系统 3.0 用户列表 `{id, username, display_name, dept_code?, status}`，"
        "按 username upsert 本地 SysUser，并将 id 写入匹配员工的 `system_account_id` "
        "（匹配顺序：已有绑定 → SysUser.employee_id → emp_no=username）。"
        "不接收、不存储 3.0 密码或其它真实凭证。"
    ),
)
def post_sync_users(
    body: SyncUsersIn,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("btn.integration.sync")),
):
    return sync_users(db, body.users)


@router.post(
    "/validate-training-before-grant",
    response_model=ValidateTrainingOut,
    summary="开权前培训闸门校验",
    description=(
        "供 Web / 3.0 在真正 grant 前预检。"
        "媒体联络人且 scopes 含 wipe 或 outbound 时，须 safety + sop + wipe_r2 "
        "均为 passed 且 valid_until>=今天；返回 ok/fail 及缺失课程，不写权限事件。"
        "身份可用 employee_id 或 system_account_id。"
    ),
)
def post_validate_training(
    body: ValidateTrainingIn,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.integration.read")),
):
    return validate_training_before_grant(
        db,
        employee_id=body.employee_id,
        system_account_id=body.system_account_id,
        scopes=body.scopes,
    )


@router.get(
    "/pending-revokes",
    response_model=list[PendingRevokeOut],
    summary="待 T+0 停权名单",
    description=(
        "关键岗位因离职（leave/resigned/left 或 leave_date 已到）或已登记 "
        "leave/project_end 的 pending 回收事件，须 T+0 立即停权。"
        "3.0 执行后应调用 POST /permission-callback 回写。"
    ),
)
def get_pending_revokes(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.integration.read")),
):
    return list_pending_revokes(db)


@router.post(
    "/permission-callback",
    response_model=PermissionEventOut,
    summary="3.0 开权/停权执行回调",
    description=(
        "综合系统 3.0 报告 grant/revoke 已执行。"
        "若该员工存在同类型 pending 的 PermissionEvent 则更新为完成；否则新增一条 T08 事件。"
        "写入 operator/reason/external_ref，并记一条 permissions 同步日志。"
    ),
)
def post_permission_callback(
    body: PermissionCallbackIn,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_perm("api.integration.write")),
):
    return apply_permission_callback(db, body)
