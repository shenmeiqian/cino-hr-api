# Phase 1 — FE/BE 权限码对齐表

日期：2026-09-04（Asia/Shanghai）  
原则：前端 `Perm` / `hasPerm(code)` 与后端 `require_perm(code)` **使用同一权限码**；无权限按钮隐藏，直接调 API 返回 **403**。

| UI 按钮 / 操作 | FE 权限码 | API | BE require_perm |
|---|---|---|---|
| 新建员工 | `btn.employees.create` | `POST /api/v1/employees` | `btn.employees.create` |
| 编辑员工 | `btn.employees.edit` | `PATCH /api/v1/employees/{id}` | `btn.employees.edit` |
| 新建招聘 | `btn.recruiting.create` | `POST /api/v1/recruiting` 等写接口 | `btn.recruiting.create` |
| 招聘提交审批 | `btn.recruiting.submit` | `POST /api/v1/workflows/submit` (recruiting) | `btn.recruiting.submit` |
| 新建入职 | `btn.onboarding.create` | `POST /api/v1/onboarding` | `btn.onboarding.create` |
| 入职提交审批 | `btn.onboarding.submit` | `POST /api/v1/workflows/submit` (onboarding) | `btn.onboarding.submit` |
| 登记合同 | `btn.contracts.create` | `POST /api/v1/contracts` | `btn.contracts.create` |
| 合同提交审批 | `btn.contracts.submit` | `POST /api/v1/workflows/submit` (contracts) | `btn.contracts.submit` |
| 新建培训 | `btn.trainings.create` | `POST /api/v1/trainings` | `btn.trainings.create` |
| 登记培训通过 | `btn.trainings.pass` | `POST /api/v1/trainings/{id}/pass` | `btn.trainings.pass` |
| 新建考勤异常 | `btn.attendance.create` | `POST /api/v1/attendance-exceptions` | `btn.attendance.create` |
| 上传证据 | `btn.evidences.create` | `POST /api/v1/evidences` | `btn.evidences.create` |
| 新建工单 | `btn.tickets.create` | `POST /api/v1/tickets` | `btn.tickets.create` |
| 工单提交审批 | `btn.tickets.submit` | `POST /api/v1/workflows/submit` (tickets) | `btn.tickets.submit` |
| 发起紧急用工 | `btn.emergency.create` | `POST /api/v1/emergency` | `btn.emergency.create` |
| 紧急用工提交审批 | `btn.emergency.submit` | `POST /api/v1/workflows/submit` (emergency) | `btn.emergency.submit` |
| KPI 跑批 | `btn.kpi.run` | `POST /api/v1/kpi/...` | `btn.kpi.run` |
| 新建流程 | `btn.workflows.create` | `POST /api/v1/workflows/definitions` | `btn.workflows.create` |
| 保存流程 | `btn.workflows.save` | `PUT /api/v1/workflows/definitions/{id}` | `btn.workflows.save` |
| 发布流程 | `btn.workflows.publish` | `POST /api/v1/workflows/definitions/{id}/publish` | `btn.workflows.publish` |
| 启动实例 | `btn.workflows.start` | `POST /api/v1/workflows/instances` | `btn.workflows.start` |
| 审批推进 | `btn.workflows.advance` | `POST /api/v1/workflows/instances/{id}/advance` | `btn.workflows.advance` |
| 上传文件 | `btn.files.upload` | `POST /api/v1/files` | `btn.files.upload` |
| 删除文件 | `btn.files.delete` | `DELETE /api/v1/files/{id}` | `btn.files.delete` |
| 发送通知 | `btn.notifications.send` | `POST /api/v1/notifications/send` | `btn.notifications.send` |
| 新建用户 | `btn.sys.users.create` | `POST /api/v1/sys/users` | `btn.sys.users.create` |
| 编辑/冻结/重置密码 | `btn.sys.users.edit` | `PUT/POST /api/v1/sys/users/...` | `btn.sys.users.edit` |
| 编辑角色/保存权限树 | `btn.sys.roles.edit` | `POST/PUT /api/v1/sys/roles` | `btn.sys.roles.edit` |
| 编辑菜单 | `btn.sys.menus.edit` | `POST/PUT/DELETE /api/v1/sys/menus` | `btn.sys.menus.edit` |
| 开权 | `btn.permissions.grant` | `POST /api/v1/permissions/grant` | `btn.permissions.grant` |
| 停权 | `btn.permissions.revoke` | `POST /api/v1/permissions/revoke` | `btn.permissions.revoke` |
| 编制/岗位写 | （页面入口 menu.org） | `POST/PATCH/DELETE /api/v1/headcounts`、`POST/PATCH /api/v1/positions` | `api.org.write` |

只读菜单权限：`menu.*` 用于列表/详情 GET 与侧栏可见性。

树结构：`SysPermission.parent_id` — 按钮/API 挂在对应 `menu.*` 下；角色编辑器展示「菜单 → 按钮」嵌套勾选。
