# CINO HR API（人事微服务 MVP）

基于《人事主管 KPI V2.2》字段表 **T01–T15** 的 FastAPI 微服务，面向 CINO 回收公司演示与联调。

## 技术栈

| 项 | 说明 |
|---|---|
| Web | FastAPI + OpenAPI `/docs` |
| ORM | SQLAlchemy 2.x，`create_all`（MVP；生产可切 Alembic） |
| DB | 默认 SQLite；可切 Postgres |
| Schema | Pydantic v2 |
| 鉴权 | 请求头 `X-API-Key`（环境变量 `API_KEY`，默认 `demo-key`） |

## 启动方式

### Docker（推荐本地 / 演示）

默认生产向配置：镜像内拷贝源码（**不** bind-mount），SQLite 写到 named volume `hr_data`。容器启动时 `docker/entrypoint.sh` 会执行 `python -m app.seed`（空库建表并写入演示数据；已有数据则跳过核心 seed），再启动 uvicorn。

```bash
# 推荐：基础镜像走本机 Docker 镜像加速；pip 走本机 pip.conf
bash scripts/compose.sh up --build
# 后台: bash scripts/compose.sh up --build -d
```

也可以直接 `docker compose up --build`。基础镜像同样走本机 Docker `registry-mirrors`；pip 则用官方 PyPI，除非你导出了 `PIP_INDEX_URL`。

仓库不写死任何国家的镜像站。换国家时只改本机 Docker / pip 配置即可。

| 项 | 地址 / 值 |
|---|---|
| 健康检查 | http://localhost:8000/health → `{"status":"ok",...}` |
| Swagger | http://localhost:8000/docs |
| 默认 API Key | 请求头 `X-API-Key: demo-key`（环境变量 `API_KEY`） |
| SQLite 数据 | volume `hr_data` → 容器内 `/data/cino_hr.db` |

停止：`docker compose down`。保留数据 volume：不要加 `-v`。

本地热重载（bind-mount 源码，仅开发用）：

```bash
bash scripts/compose.sh -f docker-compose.yml -f docker-compose.dev.yml up --build
```

可选 Postgres（profile `postgres`）：

```bash
DATABASE_URL=postgresql+psycopg2://cino:cino@db:5432/cino_hr \
  bash scripts/compose.sh --profile postgres up --build
```

### 本机直接跑

```bash
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 或: bash scripts/run.sh
```

健康检查：`GET /health`  
Swagger：http://localhost:8000/docs

### 切 Postgres（本机）

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/cino_hr"
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 与综合系统 3.0 账号绑定

员工表（T01）字段 **`system_account_id`** 用于绑定综合系统 3.0 账号：

- 创建/更新员工时可写入，例如 `sys3-media-1001`
- 查询：`GET /api/v1/employees?system_account_id=sys3-media-1001`
- Seed 已写入示例：`sys3-media-1001` / `sys3-media-1002` / `sys3-hr-2001` / `sys3-temp-3001`

联调建议：综合系统侧以 `system_account_id` 为外键，本服务以 `emp_no` / `id` 为主键。

## Web / 综合系统 3.0 如何调用对接 API

前缀：`/api/v1/integration/`（OpenAPI 标签 **综合系统3.0-integration**）。

鉴权（二选一）：

- Web 管理端：登录后 `Authorization: Bearer <token>`（admin 具备全部对接权限）
- 综合系统 3.0 / 脚本：`X-API-Key: demo-key`（环境变量 `API_KEY`）

**本服务不保存、不转发 3.0 的真实账号密码或环境密钥。** Seed 仅有演示配置 `https://sys3.example.invalid`。3.0 作为客户端调用本 API；若 3.0 需要回调本服务，在 3.0 侧自行配置本服务地址与 API Key。

| 方法 | 路径 | 说明 | 典型调用方 |
|---|---|---|---|
| GET | `/api/v1/integration/sync/status` | 演示配置 + 最近同步时间/数量 + 绑定计数 | Web 管理端 |
| POST | `/api/v1/integration/sync/users` | 推送 3.0 用户 `{id, username, display_name, dept_code?, status}`；按 username upsert `SysUser`，`id` 写入员工 `system_account_id` | 3.0 或 Web 触发同步 |
| POST | `/api/v1/integration/validate-training-before-grant` | 开权前预检。媒体联络人 + `wipe`/`outbound` 须 `safety`+`sop`+`wipe_r2` 有效；返回 `ok`/`missing_courses` | Web 开权页、3.0 授权前 |
| GET | `/api/v1/integration/pending-revokes` | 关键岗离职/项目结束须 **T+0** 停权的名单 | Web、3.0 拉取待办 |
| POST | `/api/v1/integration/permission-callback` | 3.0 报告 grant/revoke 已执行 → 写入/完成 T08 `PermissionEvent` | 3.0 回调 |

示例：

```bash
# 健康检查 + 培训闸门预检（seed 后：1001 无培训失败，1002 已培训通过）
bash scripts/demo_integration.sh http://127.0.0.1:8000

# 3.0 推送用户（id 即 system_account_id）
curl -s -X POST http://127.0.0.1:8000/api/v1/integration/sync/users \
  -H 'X-API-Key: demo-key' -H 'Content-Type: application/json' \
  -d '{"users":[{"id":"sys3-media-1001","username":"zhang.media","display_name":"张媒体","dept_code":"HR","status":"active"}]}'

# 3.0 停权执行后回调
curl -s -X POST http://127.0.0.1:8000/api/v1/integration/permission-callback \
  -H 'X-API-Key: demo-key' -H 'Content-Type: application/json' \
  -d '{"system_account_id":"sys3-media-1001","event_type":"revoke","scopes":["wipe"],"trigger":"leave","status":"done","operator":"sys3"}'
```

权限码：`menu.integration` / `btn.integration.sync` / `api.integration.read` / `api.integration.write`。

## 关键业务规则

### 1. 权限授予培训闸门

`POST /api/v1/permissions/grant`

若员工 `is_media_contact=true` 且 scopes 含 `wipe` 或 `outbound`，须同时满足：

- 培训课程 `safety`、`sop`、`wipe_r2` 均存在
- `status=passed` 且 `valid_until >= 今天`

否则返回 **HTTP 403**（中文错误信息）。

### 2. 权限回收 T+0

`POST /api/v1/permissions/revoke`

若员工 `is_critical_role=true` 且 `trigger` 为 `leave` 或 `project_end`，则：

- `due_at = now`（T+0 立即到期）
- `status = pending`

### 3. KPI 批次计算（V2.2）

`POST /api/v1/kpi/batch/{yyyy_mm}/run` 将结果写入 T15 `hr_manager_scores`。

响应含 `scheme=V2.2`、`scores[]`（条款 3.1–3.12 明细，R2/ISO 分列 3.12/3.13）及 `total_weighted_score`（满分 100）。Web 可直接用 `kpi_code` / `kpi_name` / `weight` / `score` / `weighted_score` / `detail` 展示拆分。

## KPI 条款映射表（T11 默认，人事主管 KPI V2.2）

| kpi_code | 名称 | 来源 | 权重（分） |
|---|---|---|---|
| 3.1 | 编制到岗率 | T02 | 12 |
| 3.2 | 招聘闭环完成 | T04 | 6 |
| 3.3 | 人员流失控制 | T01 | 4 |
| 3.4 | 岗位库完整性 | T03 | 10 |
| 3.5 | 先定岗后进人 | T05 | 8 |
| 3.6 | 合同签署合规 | T06 | 8 |
| 3.7 | 培训合格与有效期 | T07 | 10 |
| 3.8 | 关键权限停权T+0 | T08 | 8 |
| 3.9 | 考勤异常闭环 | T09 | 6 |
| 3.10 | 岗位JD发布 | T03 | 12 |
| 3.11 | KPI条款映射覆盖 | T11 | 6 |
| 3.12 | R2准入培训 | T07 | 5 |
| 3.13 | ISO证据完备 | T14 | 5 |

`weighted_score = score(0–100) × weight / 100`。可通过 `POST /api/v1/scorecard-mappings` 增补；`GET /api/v1/scorecard-mappings` 查看（会确保 V2.2 默认条款存在）。

## 主要 API 列表

| 方法 | 路径 | 表 | 说明 |
|---|---|---|---|
| POST/GET | `/api/v1/departments` | — | 部门 |
| CRUD | `/api/v1/employees` | T01 | 员工（含 system_account_id） |
| CRUD | `/api/v1/headcounts` | T02 | 编制计划 |
| CRUD | `/api/v1/positions` | T03 | 岗位/JD（含 clauses） |
| CRUD | `/api/v1/recruiting` | T04 | 招聘需求 |
| CRUD | `/api/v1/onboarding` | T05 | 入职 |
| CRUD | `/api/v1/contracts` | T06 | 合同 |
| CRUD | `/api/v1/trainings` | T07 | 培训 |
| POST | `/api/v1/permissions/grant` | T08 | 授权（培训闸门） |
| POST | `/api/v1/permissions/revoke` | T08 | 回收（关键岗 T+0） |
| GET | `/api/v1/permissions/events` | T08 | 权限事件列表 |
| CRUD | `/api/v1/attendance-exceptions` | T09 | 考勤异常 |
| POST/GET | `/api/v1/performance-batches` | T10 | 绩效批次 |
| POST/GET | `/api/v1/scorecard-mappings` | T11 | KPI 映射 |
| POST/GET | `/api/v1/tickets` | T12 | 工单（P1） |
| POST/GET/PATCH | `/api/v1/emergency-approvals` | T13 | 紧急审批（P1） |
| CRUD | `/api/v1/evidences` | T14 | 证据附件 |
| POST | `/api/v1/kpi/batch/{yyyy_mm}/run` | T15 | V2.2 跑批写分（3.1–3.12 明细） |
| GET | `/api/v1/kpi/scores` | T15 | 查询得分 |
| GET | `/api/v1/integration/sync/status` | — | 3.0 同步状态 |
| POST | `/api/v1/integration/sync/users` | T01 | 同步 3.0 用户并绑定账号 |
| POST | `/api/v1/integration/validate-training-before-grant` | T07 | 开权前培训闸门预检 |
| GET | `/api/v1/integration/pending-revokes` | T08 | T+0 待停权名单 |
| POST | `/api/v1/integration/permission-callback` | T08 | 3.0 开权/停权回调 |

所有业务接口（除 `/health`、`/docs`）需头：`X-API-Key: demo-key`。

## 演示 curl

```bash
# 无培训 → 403
curl -s -X POST http://127.0.0.1:8000/api/v1/permissions/grant \
  -H 'X-API-Key: demo-key' -H 'Content-Type: application/json' \
  -d '{"employee_id":1,"scopes":["wipe","outbound"]}'

# 已培训员工（seed 中 E1002）→ 200
curl -s -X POST http://127.0.0.1:8000/api/v1/permissions/grant \
  -H 'X-API-Key: demo-key' -H 'Content-Type: application/json' \
  -d '{"employee_id":2,"scopes":["wipe","outbound"]}'

# KPI 跑批
curl -s -X POST http://127.0.0.1:8000/api/v1/kpi/batch/2026-09/run \
  -H 'X-API-Key: demo-key'
```

Seed 说明：E1001=媒体联络人无培训；E1002=媒体联络人三项培训已通过。

## 测试

```bash
pytest -q
```

覆盖：培训闸门失败/成功、关键岗位 leave 回收 `due_at=T+0`、综合系统 3.0 对接与 KPI V2.2 权重明细。

联调脚本（需服务已启动）：

```bash
bash scripts/demo_integration.sh
```

## 目录结构

```
cino-hr-api/
├── app/
│   ├── main.py
│   ├── config.py / database.py / auth.py / seed.py
│   ├── models/          # T01–T15 + integration
│   ├── schemas/
│   ├── routers/         # 含 integration（综合系统3.0）
│   └── services/        # permission + kpi V2.2 + integration
├── tests/
├── docker/
│   └── entrypoint.sh   # seed then uvicorn
├── scripts/run.sh
├── scripts/compose.sh   # docker compose + 本机 pip 源
├── scripts/demo_integration.sh
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```
