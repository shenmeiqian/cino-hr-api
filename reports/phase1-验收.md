# 阶段 1 验收记录 — 身份与授权底座

日期：2026-09-04（Asia/Shanghai）  
范围：仅 Phase 1；未实施 Phase 2–6（组织衔接 / 审批引擎 / 招聘闭环 / 文件·SSO·通知 / 压测）。

## 交付摘要

- **数据模型**：`SysUser` / `SysRole` / `SysPermission(parent_id 树, type=menu|button|api)` / `SysUserRole` / `SysRolePermission` / `SysMenu(parent_id 树)` / `SysToken`
- **鉴权**：`POST /api/v1/auth/login`、`GET /me`、`POST /logout`；Bearer 会话；`X-API-Key: demo-key` 破窗超管
- **管理 API**：用户 CRUD+挂角色；角色 CRUD+**权限树全量替换**；`GET /sys/permissions/tree`；菜单 CRUD + `GET /sys/menus/tree`（按用户权限过滤，API Key=全部）
- **后端强制**：业务写接口使用同一权限码（`btn.*` / `api.*`），缺失返回 **403** 中文 detail
- **前端**：Login；`AuthContext.hasPerm`；侧栏**仅**渲染 `/sys/menus/tree` 嵌套可展开；`/sys/users|roles|permissions|menus`；无 `btn.*` 隐藏按钮；无菜单权限 → NoAccess
- **DB**：本阶段为对齐 `parent_id` **已清空重建 sqlite**（`rm cino_hr.db` + 启动 seed）。说明：若本地仍有旧库且含 `parent_code` 列，请删除 `cino_hr.db` 后重启 API。

## 验收对照

| # | 标准 | 结果 |
|---|------|------|
| 1 | admin 在角色管理改权限 → hr 重新登录 → 菜单/按钮变化 | ✅ 实测：去掉 hr 的 `menu.employees` 等后，侧栏「人事业务」不再含「员工花名册」；`POST /employees` 亦 403 |
| 2 | 无权限 API → 403 | ✅ viewer/hr 缺 `btn.employees.create` 时返回 `无权限执行此操作（缺少权限码 …）` |
| 3 | 嵌套动态菜单来自 DB；菜单配置可新增 | ✅ 顶级：工作台/人事业务/审批中心/系统管理；admin 新增「Phase1验收菜单」后出现在工作台子级 |
| 4 | 双仓 commit + push | ✅（见 git） |
| 5 | 演示账号 | 见下 |

## 演示账号

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| admin | admin123 | admin | 全部权限（含系统管理） |
| hr | hr123 | hr | 人事/审批菜单与按钮；**无**系统管理 |
| viewer | viewer123 | viewer | 仅菜单只读（无写按钮权限） |

破窗：`X-API-Key: demo-key`

## 服务

- API：`http://127.0.0.1:8000`
- Web：`http://127.0.0.1:5173`

## 刻意未做（后续阶段）

文件存储切换、SSO 实配、通知渠道、审批拖拽闭环、招聘入职流水线、压测报告。
