# 阶段 3 验收记录 — 审批引擎 + 待办详情

日期：2026-09-04（Asia/Shanghai）

## 交付

- 流程定义拖拽设计（开始/审批/条件/结束），保存/发布（审批岗=岗位 code）  
- 实例：提交 / 通过 / 驳回 + `WorkflowHistory`  
- **待办列表 + 详情**：单据快照 JSON、节点、流转历史、审批意见；通过/驳回仅在待办详情  
- 业务单据页仅「提交审批」（`SubmitApprovalBtn`），无散落通过/驳回；设计器「运行实例」页亦引导至待办

## 验收

| # | 标准 | 结果 |
|---|------|------|
| 1 | 提交审批 → 待办可见 | ✅ `/workflows/submit` + `/workflows/todos` 按岗位 code 过滤 |
| 2 | 详情含快照与历史 | ✅ `GET /workflows/instances/{id}` + Todos 详情弹层 |
| 3 | 单据页无通过/驳回 | ✅ Recruiting/Onboarding/Contracts/Tickets/Emergency 仅提交 |
