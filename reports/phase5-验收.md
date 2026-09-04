# 阶段 5 验收记录 — 文件 / SSO / 通知

日期：2026-09-04（Asia/Shanghai）

## 交付

- **文件**：`FILE_STORAGE_BACKEND=local|s3|database`；上传可 Form `backend` 覆盖；本地与 database 实测可用；S3 需配置密钥否则 400 提示  
- **SSO**：OIDC 登录/回调骨架；`GET /auth/sso/status` 未配置时返回 hint；账密登录始终可用  
- **通知**：email / sms / wecom / dingtalk / feishu；无密钥 **dry-run** 写 `notification_logs`；审批推进可触发邮件 dry-run

## 环境变量

见 `/workspace/cino-hr-api/.env.example`（SMTP_*、OIDC_*、S3_*、WECOM/DINGTALK/FEISHU webhook、SMS_*）。

## 验收

| # | 标准 | 结果 |
|---|------|------|
| 1 | 本地/库上传可用 | ✅ database 后端上传成功 |
| 2 | SSO 有配置说明 | ✅ status hint + .env.example |
| 3 | 通知 dry-run | ✅ 未配 SMTP 记 dry_run（需 btn.notifications.send，admin） |
