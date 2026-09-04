# 阶段 4 验收记录 — 招聘入职业务闭环

日期：2026-09-04（Asia/Shanghai）

## 交付

- 统一入口「招聘入职闭环」：时间轴  
  `编制 → 需求 → 候选人 → 审批 → 入职单 → 合同 → 培训 → 开权 → 完成`  
- 阶段门禁：`POST /recruiting/{id}/advance`（check_headcount / open_req / set_candidate / submit_approval / gen_onboarding / gen_contract / eval_grant）  
- **开权**：培训闸门后 `auto_grant_if_ready`；看板 `/recruiting/stats/grant` + Dashboard 卡片自动统计  
- 开权业务不作为日常独立入口（保留系统「开权审计日志」）

## 验收

| # | 标准 | 结果 |
|---|------|------|
| 1 | 闭环时间轴可追踪 | ✅ Recruiting 详情时间轴 + timeline API |
| 2 | 上一步未完成不可乱跳 | ✅ pipeline_service 阶段校验 |
| 3 | 开权为自动统计 | ✅ grant_stats + Dashboard |

