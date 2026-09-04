"""KPI batch computation for T15 (人事主管 KPI V2.2 placeholder formulas)."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.headcount import HeadcountPlan
from app.models.permission import PermissionEvent
from app.models.performance import HrManagerScore, PerformanceBatch, ScorecardMapping
from app.models.training import Training

# ---------------------------------------------------------------------------
# 公式说明（MVP 占位，可在 T11 scorecard_mappings 中覆盖）
# 1. staffing_rate  编制到位率
#    raw = sum(actual_count) / sum(planned_count)   （当月 headcount_plans）
#    score = min(100, raw * 100)
# 2. training_fail_count  培训不合格次数
#    raw = count(trainings where status=failed)
#    score = max(0, 100 - raw * 10)
# 3. revoke_overtime_count  关键权限回收超时次数
#    raw = count(permission_events where event_type=revoke and status=overdue)
#         + count(pending revoke with due_at < now) 视为逾期
#    score = max(0, 100 - raw * 20)
# ---------------------------------------------------------------------------

DEFAULT_KPIS = [
    {
        "kpi_code": "staffing_rate",
        "kpi_name": "编制到位率",
        "source_table": "T02",
        "formula": "sum(actual)/sum(planned)*100，满分100",
        "weight": 0.4,
        "target_value": ">=95%",
        "unit": "%",
    },
    {
        "kpi_code": "training_fail_count",
        "kpi_name": "培训不合格次数",
        "source_table": "T07",
        "formula": "failed 培训数；score=max(0,100-raw*10)",
        "weight": 0.3,
        "target_value": "0",
        "unit": "次",
    },
    {
        "kpi_code": "revoke_overtime_count",
        "kpi_name": "权限回收逾期次数",
        "source_table": "T08",
        "formula": "revoke overdue(+pending past due)；score=max(0,100-raw*20)",
        "weight": 0.3,
        "target_value": "0",
        "unit": "次",
    },
]


def ensure_default_mappings(db: Session) -> None:
    for item in DEFAULT_KPIS:
        exists = (
            db.query(ScorecardMapping)
            .filter(ScorecardMapping.kpi_code == item["kpi_code"])
            .first()
        )
        if not exists:
            db.add(ScorecardMapping(**item))
    db.commit()


def _calc_staffing_rate(db: Session, year_month: str) -> tuple[float, float, str]:
    plans = db.query(HeadcountPlan).filter(HeadcountPlan.year_month == year_month).all()
    if not plans:
        # fallback: active employees vs sum of planned if any global
        active = db.query(func.count(Employee.id)).filter(Employee.status == "active").scalar() or 0
        return float(active), min(100.0, float(active) * 10), f"无编制计划，按在职人数={active}占位"
    planned = sum(p.planned_count for p in plans) or 0
    actual = sum(p.actual_count for p in plans) or 0
    raw = (actual / planned) if planned else 0.0
    score = min(100.0, raw * 100.0)
    return raw, score, f"actual={actual}/planned={planned}"


def _calc_training_fails(db: Session) -> tuple[float, float, str]:
    raw = db.query(func.count(Training.id)).filter(Training.status == "failed").scalar() or 0
    score = max(0.0, 100.0 - float(raw) * 10.0)
    return float(raw), score, f"failed_trainings={raw}"


def _calc_revoke_overtime(db: Session) -> tuple[float, float, str]:
    now = datetime.utcnow()
    overdue = (
        db.query(func.count(PermissionEvent.id))
        .filter(
            PermissionEvent.event_type == "revoke",
            PermissionEvent.status == "overdue",
        )
        .scalar()
        or 0
    )
    pending_past = (
        db.query(func.count(PermissionEvent.id))
        .filter(
            PermissionEvent.event_type == "revoke",
            PermissionEvent.status == "pending",
            PermissionEvent.due_at.isnot(None),
            PermissionEvent.due_at < now,
        )
        .scalar()
        or 0
    )
    raw = overdue + pending_past
    score = max(0.0, 100.0 - float(raw) * 20.0)
    return float(raw), score, f"overdue={overdue}, pending_past_due={pending_past}"


CALCULATORS = {
    "staffing_rate": lambda db, ym: _calc_staffing_rate(db, ym),
    "training_fail_count": lambda db, ym: _calc_training_fails(db),
    "revoke_overtime_count": lambda db, ym: _calc_revoke_overtime(db),
}


def run_kpi_batch(db: Session, year_month: str) -> tuple[PerformanceBatch, list[HrManagerScore], float]:
    if len(year_month) != 7 or year_month[4] != "-":
        raise HTTPException(status_code=400, detail="year_month 格式须为 YYYY-MM")

    ensure_default_mappings(db)

    batch = (
        db.query(PerformanceBatch).filter(PerformanceBatch.year_month == year_month).first()
    )
    if not batch:
        batch = PerformanceBatch(year_month=year_month, status="running", started_at=datetime.utcnow())
        db.add(batch)
        db.commit()
        db.refresh(batch)
    else:
        batch.status = "running"
        batch.started_at = datetime.utcnow()
        db.commit()

    # clear previous scores for this month
    db.query(HrManagerScore).filter(HrManagerScore.year_month == year_month).delete()
    db.commit()

    mappings = db.query(ScorecardMapping).all()
    scores: list[HrManagerScore] = []
    total_weighted = 0.0

    for m in mappings:
        calc = CALCULATORS.get(m.kpi_code)
        if calc:
            raw, score, detail = calc(db, year_month)
        else:
            raw, score, detail = 0.0, 0.0, "无计算器，占位0分"
        weighted = score * (m.weight or 0.0)
        total_weighted += weighted
        row = HrManagerScore(
            year_month=year_month,
            kpi_code=m.kpi_code,
            kpi_name=m.kpi_name,
            raw_value=raw,
            score=score,
            weight=m.weight or 0.0,
            weighted_score=weighted,
            detail=detail,
        )
        db.add(row)
        scores.append(row)

    batch.status = "closed"
    batch.closed_at = datetime.utcnow()
    db.commit()
    for s in scores:
        db.refresh(s)
    db.refresh(batch)
    return batch, scores, total_weighted
