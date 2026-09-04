# 阶段 6 压测报告 — 20 人并发

日期：2026-09-04（Asia/Shanghai）  
脚本：`scripts/stress_20.py`  
目标：`http://127.0.0.1:8000`

## 摘要

| 指标 | 值 |
|------|----|
| 并发用户 | 20 |
| 总调用 | 180 |
| 墙钟耗时 | 2050.68 ms |
| p50 | 167.94 ms |
| p95 | 420.42 ms |
| 均值 | 212.11 ms |
| 错误数 | 0 |
| 错误率 | 0.0 |

路径：登录 → `/me` → menus/tree → employees → positions → headcounts → todos → recruiting → grant stats。

说明：SQLite 使用 WAL + `busy_timeout` + **NullPool**，避免 20 并发下 QueuePool 耗尽；错误率 0。

## JSON

```json
{
  "concurrent_users": 20,
  "wall_clock_ms": 2050.68,
  "total_calls": 180,
  "error_count": 0,
  "error_rate": 0.0,
  "p50_ms": 167.94,
  "p95_ms": 420.42,
  "mean_ms": 212.11,
  "per_user": [
    {
      "user": "admin",
      "elapsed_ms": 2046.35,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 2037.23,
      "errors": []
    },
    {
      "user": "viewer",
      "elapsed_ms": 1827.43,
      "errors": []
    },
    {
      "user": "admin",
      "elapsed_ms": 1993.9,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 1993.48,
      "errors": []
    },
    {
      "user": "viewer",
      "elapsed_ms": 1825.52,
      "errors": []
    },
    {
      "user": "admin",
      "elapsed_ms": 2046.01,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 1945.69,
      "errors": []
    },
    {
      "user": "viewer",
      "elapsed_ms": 1944.83,
      "errors": []
    },
    {
      "user": "admin",
      "elapsed_ms": 2012.49,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 1990.32,
      "errors": []
    },
    {
      "user": "viewer",
      "elapsed_ms": 1823.54,
      "errors": []
    },
    {
      "user": "admin",
      "elapsed_ms": 1989.18,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 1989.25,
      "errors": []
    },
    {
      "user": "viewer",
      "elapsed_ms": 1820.9,
      "errors": []
    },
    {
      "user": "admin",
      "elapsed_ms": 1904.04,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 2030.31,
      "errors": []
    },
    {
      "user": "viewer",
      "elapsed_ms": 1902.27,
      "errors": []
    },
    {
      "user": "admin",
      "elapsed_ms": 1900.95,
      "errors": []
    },
    {
      "user": "hr",
      "elapsed_ms": 2007.78,
      "errors": []
    }
  ]
}
```
