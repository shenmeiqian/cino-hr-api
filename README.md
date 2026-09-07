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
docker compose up --build
# 后台: docker compose up --build -d
```

| 项 | 地址 / 值 |
|---|---|
| 健康检查 | http://localhost:8000/health → `{"status":"ok",...}` |
| Swagger | http://localhost:8000/docs |
| 默认 API Key | 请求头 `X-API-Key: demo-key`（环境变量 `API_KEY`） |
| SQLite 数据 | volume `hr_data` → 容器内 `/data/cino_hr.db` |

停止：`docker compose down`。保留数据 volume：不要加 `-v`。

本地热重载（bind-mount 源码，仅开发用）：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

可选 Postgres（profile `postgres`）：

```bash
DATABASE_URL=postgresql+psycopg2://cino:cino@db:5432/cino_hr \
  docker compose --profile postgres up --build
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

### 3. KPI 批次计算

`POST /api/v1/kpi/batch/{yyyy_mm}/run` 将结果写入 T15 `hr_manager_scores`。

## KPI 条款映射表（T11 默认）

| kpi_code | 名称 | 来源 | 公式（MVP 占位） | 权重 |
|---|---|---|---|---|
| staffing_rate | 编制到位率 | T02 | `sum(actual)/sum(planned)*100`，满分 100 | 0.4 |
| training_fail_count | 培训不合格次数 | T07 | `failed` 条数；`score=max(0,100-raw*10)` | 0.3 |
| revoke_overtime_count | 权限回收逾期次数 | T08 | revoke `overdue` + pending 且 due_at&lt;now；`score=max(0,100-raw*20)` | 0.3 |

可通过 `POST /api/v1/scorecard-mappings` 增补；`GET /api/v1/scorecard-mappings` 查看。

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
| POST | `/api/v1/kpi/batch/{yyyy_mm}/run` | T15 | 跑批写分 |
| GET | `/api/v1/kpi/scores` | T15 | 查询得分 |

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

覆盖：培训闸门失败/成功、关键岗位 leave 回收 `due_at=T+0`。

## 目录结构

```
cino-hr-api/
├── app/
│   ├── main.py
│   ├── config.py / database.py / auth.py / seed.py
│   ├── models/          # T01–T15
│   ├── schemas/
│   ├── routers/
│   └── services/        # permission + kpi
├── tests/
├── docker/
│   └── entrypoint.sh   # seed then uvicorn
├── scripts/run.sh
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```
