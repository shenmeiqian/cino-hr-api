"""Phase6: simulate 20 concurrent users hitting login + common APIs."""
from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
USERS = [
    ("admin", "admin123"),
    ("hr", "hr123"),
    ("viewer", "viewer123"),
] * 7  # 21, take 20
USERS = USERS[:20]


def one_user(idx: int, username: str, password: str) -> dict:
    t0 = time.perf_counter()
    errors = []
    latencies = []
    with httpx.Client(timeout=60.0) as client:
        def timed(method, url, **kw):
            s = time.perf_counter()
            try:
                r = client.request(method, url, **kw)
                latencies.append((url, (time.perf_counter() - s) * 1000, r.status_code))
                if r.status_code >= 400:
                    errors.append(f"{method} {url} -> {r.status_code} {r.text[:120]}")
                return r
            except Exception as e:
                latencies.append((url, (time.perf_counter() - s) * 1000, 0))
                errors.append(f"{method} {url} EXC {e}")
                return None

        login = timed("POST", f"{BASE}/api/v1/auth/login", json={"username": username, "password": password})
        token = None
        if login is not None and login.status_code == 200:
            token = login.json().get("token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        for path in [
            "/api/v1/auth/me",
            "/api/v1/sys/menus/tree",
            "/api/v1/employees",
            "/api/v1/positions",
            "/api/v1/headcounts",
            "/api/v1/workflows/todos",
            "/api/v1/recruiting",
            "/api/v1/recruiting/stats/grant",
        ]:
            timed("GET", f"{BASE}{path}", headers=headers)
    return {
        "idx": idx,
        "user": username,
        "elapsed_ms": (time.perf_counter() - t0) * 1000,
        "latencies": latencies,
        "errors": errors,
    }


def main() -> None:
    print(f"Stress: {len(USERS)} concurrent users → {BASE}")
    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = [pool.submit(one_user, i, u, p) for i, (u, p) in enumerate(USERS)]
        for f in as_completed(futs):
            results.append(f.result())
    wall = (time.perf_counter() - t0) * 1000
    all_ms = [ms for r in results for (_, ms, _) in r["latencies"]]
    err_n = sum(len(r["errors"]) for r in results)
    total_calls = len(all_ms)
    p50 = statistics.median(all_ms) if all_ms else 0
    p95 = statistics.quantiles(all_ms, n=20)[18] if len(all_ms) >= 20 else max(all_ms or [0])
    report = {
        "concurrent_users": len(USERS),
        "wall_clock_ms": round(wall, 2),
        "total_calls": total_calls,
        "error_count": err_n,
        "error_rate": round(err_n / total_calls, 4) if total_calls else 1,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "mean_ms": round(statistics.mean(all_ms), 2) if all_ms else 0,
        "per_user": [
            {
                "user": r["user"],
                "elapsed_ms": round(r["elapsed_ms"], 2),
                "errors": r["errors"][:3],
            }
            for r in sorted(results, key=lambda x: x["idx"])
        ],
    }
    out = Path("/workspace/cino-hr-api/reports/phase6-压测.md")
    md = f"""# 阶段 6 压测报告 — 20 人并发

日期：2026-09-04（Asia/Shanghai）  
脚本：`scripts/stress_20.py`  
目标：`{BASE}`

## 摘要

| 指标 | 值 |
|------|----|
| 并发用户 | {report['concurrent_users']} |
| 总调用 | {report['total_calls']} |
| 墙钟耗时 | {report['wall_clock_ms']} ms |
| p50 | {report['p50_ms']} ms |
| p95 | {report['p95_ms']} ms |
| 均值 | {report['mean_ms']} ms |
| 错误数 | {report['error_count']} |
| 错误率 | {report['error_rate']} |

路径：登录 → `/me` → menus/tree → employees → positions → headcounts → todos → recruiting → grant stats。

## JSON

```json
{json.dumps(report, ensure_ascii=False, indent=2)}
```
"""
    out.write_text(md, encoding="utf-8")
    print(md.split("## JSON")[0])
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
