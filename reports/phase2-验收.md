# 阶段 2 验收记录 — 组织与主数据衔接

日期：2026-09-04（Asia/Shanghai）  
范围：仅 Phase 2 交付项（随后已继续 3–6，见各阶段报告）。

## 交付摘要

1. **部门 / 岗位库 / 批准编制**  
   - API：`/departments`、`/positions`、`/headcounts` CRUD（写权限 `api.org.write`）  
   - 前端「编制与岗位」：部门/编制/岗位中文 UI，岗位可编辑

2. **岗位 ↔ 角色**  
   - 表 `position_roles (position_id, role_id)`  
   - `GET/PUT /positions/{id}/roles`；创建/更新岗位亦可带 `role_ids`  
   - 配置 `SYNC_ROLES_FROM_POSITION`（默认 `true`）  
   - **有效角色** = 直接 `SysUserRole` ∪ 岗位绑定角色（读时合并，不改写用户角色表）  
   - 岗位来源：`SysUser.position_id` **或** 关联 `Employee.position_id`  
   - `/auth/me` 返回 `roles`（有效）、`direct_roles`、`position_roles`、`sync_roles_from_position`

3. **员工 ↔ SysUser 双向绑定**  
   - `Employee.sys_user_id` ↔ `SysUser.employee_id` 互相同步  
   - 花名册：绑定下拉、列表显示 `sys_username`、「开用户」快捷创建  
   - 用户管理：绑定员工、显示员工工号/姓名

4. **审批节点 = 本地岗位 code**  
   - 设计器下拉选择 `position.code`（禁止自由文本）  
   - 保存/发布服务端校验；非法 code → 400  
   - Seed：`ONBOARD-APPROVAL` 等使用 `HR-MANAGER` / `MEDIA-CONTACT`

## 验收对照

| # | 标准 | 结果 |
|---|------|------|
| 1 | 岗位绑角色后，任职用户 `/me` 权限含岗位角色 | ✅ admin 直挂 admin，岗位 HR-MANAGER→hr，`roles=["admin","hr"]` |
| 2 | 员工绑用户双向一致 | ✅ E2001↔hr、E1002↔viewer |
| 3 | 审批节点须有效岗位 code | ✅ `NOT-A-POS` 保存返回 400 |
| 4 | 编制与岗位中文端到端 | ✅ Org 页 CRUD + 角色勾选 |

## Demo 说明

- **岗位→角色同步**：在「编制与岗位」编辑岗位勾选角色 → 用户挂该岗位或绑该岗员工 → **重新登录** 看 `/me.roles`  
- **员工↔用户**：花名册编辑选 SysUser，或点「开用户」；用户页亦可绑员工  
- **审批岗位**：流程设计右侧下拉选岗位 code 后保存

## 环境变量

`SYNC_ROLES_FROM_POSITION=true|false`（见 `.env.example`）
