# 阶段 1 补强验收 — 按钮权限 / FE·BE 对齐 / 用户岗位与冻结

日期：2026-09-04（Asia/Shanghai）  
范围：**仅 Phase 1 补强**；未启动 Phase 2–6。  
依据用户反馈三件套。

## 反馈对照

| # | 反馈 | 处理 |
|---|------|------|
| 1 | 菜单树缺少按钮级权限控制 | 角色权限树展示 **菜单 → 按钮/API** 嵌套（`SysPermission.parent_id`）；菜单配置页增加「按钮权限」列，列出该页关联的 `btn.*` |
| 2 | 前后端权限没对齐 | 新增 `reports/perm-map.md`；补齐 workflows / headcounts / positions 写接口 `require_perm`；员工「编辑」按钮补 `Perm(btn.employees.edit)`；`/workflows/submit` 按 business_type 校验对应 `btn.*.submit` |
| 3 | 用户端缺少岗位、冻结等 | `SysUser` 扩展 `position_id` / `phone` / `email` / `last_login_at`；状态 `active\|frozen\|disabled`；冻结/解冻/重置密码 API；冻结使 Token 失效且登录提示明确；列表支持状态/岗位筛选 |

## 验收实测（API）

- 权限树：`menu.employees` 下可见 `btn.employees.create` / `btn.employees.edit` …
- 菜单配置：员工花名册 `button_perms` = 新建员工 / 编辑员工
- 冻结 viewer → 旧 Token 失效；再登录返回 `账号已冻结，请联系管理员解冻后再登录`
- viewer 直接 `POST /employees` → **403**（`btn.employees.create`）
- viewer `POST /workflows/definitions` → **403**（`btn.workflows.create`）
- viewer `POST /workflows/submit` recruiting → **403**（`btn.recruiting.submit`）

## 演示账号

| 用户 | 密码 | 说明 |
|------|------|------|
| admin | admin123 | 全权限；已关联岗位 HR-MANAGER |
| hr | hr123 | 人事权限，无系统管理 |
| viewer | viewer123 | 只读菜单；无写按钮 |

服务：API `:8000` / Web `:5173`

## 刻意未做

Phase 2（岗位↔角色自动同步等）及以后阶段 — **等待用户对本 Phase 1 补强再验收**。
