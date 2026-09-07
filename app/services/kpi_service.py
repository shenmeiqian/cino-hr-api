"""KPI batch computation for T15 — 人事主管 KPI V2.2（条款 3.1–3.12 明细）。

权重（百分制满分 100）：
到岗12、招聘6、流失4、岗位库10、先定岗8、合同8、培训10、停权8、
考勤6、发布12、映射6、R2准入5、ISO5。
其中 R2 与 ISO 分列（代码 3.12 / 3.13），便于 Web 展示合规项拆分。
weighted_score = score(0–100) × weight / 100。
"""
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceException
from app.models.contract import Contract
from app.models.employee import Employee
from app.models.evidence import Evidence
from app.models.headcount import HeadcountPlan
from app.models.onboarding import Onboarding
from app.models.permission import PermissionEvent
from app.models.performance import HrManagerScore, PerformanceBatch, ScorecardMapping
from app.models.position import Position, PositionClause
from app.models.recruiting import RecruitingReq
from app.models.training import Training
from app.models.workflow import WorkflowDefinition

KPI_SCHEME = "V2.2"
KPI_MAX_SCORE = 100.0

# 旧版 MVP 占位条款，跑批时不再计入，避免权重被稀释
LEGACY_KPI_CODES = ("staffing_rate", "training_fail_count", "revoke_overtime_count")

DEFAULT_KPIS = [
    {
        "kpi_code": "3.1",
        "kpi_name": "编制到岗率",
        "source_table": "T02",
        "formula": "sum(actual)/sum(planned)*100，满分100",
        "weight": 12.0,
        "target_value": ">=95%",
        "unit": "%",
        "remark": "V2.2 条款3.1 到岗 12分",
    },
    {
        "kpi_code": "3.2",
        "kpi_name": "招聘闭环完成",
        "source_table": "T04",
        "formula": "招聘单进入 onboarding/contract/trained/granted/closed 占比",
        "weight": 6.0,
        "target_value": ">=80%",
        "unit": "%",
        "remark": "V2.2 条款3.2 招聘 6分",
    },
    {
        "kpi_code": "3.3",
        "kpi_name": "人员流失控制",
        "source_table": "T01",
        "formula": "在职率=active/(active+离职)；score=在职率*100",
        "weight": 4.0,
        "target_value": "流失越低越好",
        "unit": "%",
        "remark": "V2.2 条款3.3 流失 4分",
    },
    {
        "kpi_code": "3.4",
        "kpi_name": "岗位库完整性",
        "source_table": "T03",
        "formula": "含至少一条职责条款的岗位占比",
        "weight": 10.0,
        "target_value": "100%",
        "unit": "%",
        "remark": "V2.2 条款3.4 岗位库 10分",
    },
    {
        "kpi_code": "3.5",
        "kpi_name": "先定岗后进人",
        "source_table": "T05",
        "formula": "入职单对应员工已绑定 position_id 的占比；无入职单则看员工定岗率",
        "weight": 8.0,
        "target_value": "100%",
        "unit": "%",
        "remark": "V2.2 条款3.5 先定岗 8分",
    },
    {
        "kpi_code": "3.6",
        "kpi_name": "合同签署合规",
        "source_table": "T06",
        "formula": "在职员工持有 active 合同的占比",
        "weight": 8.0,
        "target_value": "100%",
        "unit": "%",
        "remark": "V2.2 条款3.6 合同 8分",
    },
    {
        "kpi_code": "3.7",
        "kpi_name": "培训合格与有效期",
        "source_table": "T07",
        "formula": "failed 培训数；score=max(0,100-raw*10)",
        "weight": 10.0,
        "target_value": "0次不合格",
        "unit": "次",
        "remark": "V2.2 条款3.7 培训 10分",
    },
    {
        "kpi_code": "3.8",
        "kpi_name": "关键权限停权T+0",
        "source_table": "T08",
        "formula": "revoke overdue(+pending past due)；score=max(0,100-raw*20)",
        "weight": 8.0,
        "target_value": "0次逾期",
        "unit": "次",
        "remark": "V2.2 条款3.8 停权 8分",
    },
    {
        "kpi_code": "3.9",
        "kpi_name": "考勤异常闭环",
        "source_table": "T09",
        "formula": "当月 open 异常数；score=max(0,100-raw*10)",
        "weight": 6.0,
        "target_value": "及时关闭",
        "unit": "次",
        "remark": "V2.2 条款3.9 考勤 6分",
    },
    {
        "kpi_code": "3.10",
        "kpi_name": "岗位JD发布",
        "source_table": "T03",
        "formula": "active 岗位已填写 jd_summary 的占比；辅以已发布审批流",
        "weight": 12.0,
        "target_value": "100%",
        "unit": "%",
        "remark": "V2.2 条款3.10 发布 12分",
    },
    {
        "kpi_code": "3.11",
        "kpi_name": "KPI条款映射覆盖",
        "source_table": "T11",
        "formula": "V2.2 预期条款在 T11 的覆盖率",
        "weight": 6.0,
        "target_value": "13/13",
        "unit": "%",
        "remark": "V2.2 条款3.11 映射 6分",
    },
    {
        "kpi_code": "3.12",
        "kpi_name": "R2准入培训",
        "source_table": "T07",
        "formula": "媒体联络人持有有效 wipe_r2 培训的占比",
        "weight": 5.0,
        "target_value": "100%",
        "unit": "%",
        "remark": "V2.2 条款3.12 R2准入 5分",
    },
    {
        "kpi_code": "3.13",
        "kpi_name": "ISO证据完备",
        "source_table": "T14",
        "formula": "存在 ISO 相关证据则满分，否则按证据条数占位",
        "weight": 5.0,
        "target_value": "有ISO证据",
        "unit": "条",
        "remark": "V2.2 与3.12并列的 ISO 5分（明细拆分）",
    },
]

V22_CODES = tuple(item["kpi_code"] for item in DEFAULT_KPIS)


def ensure_default_mappings(db: Session) -> None:
    if LEGACY_KPI_CODES:
        db.query(ScorecardMapping).filter(ScorecardMapping.kpi_code.in_(LEGACY_KPI_CODES)).delete(
            synchronize_session=False
        )
    by_code = {m.kpi_code: m for m in db.query(ScorecardMapping).all()}
    for item in DEFAULT_KPIS:
        row = by_code.get(item["kpi_code"])
        if not row:
            db.add(ScorecardMapping(**item))
        else:
            row.kpi_name = item["kpi_name"]
            row.source_table = item["source_table"]
            row.formula = item["formula"]
            row.weight = item["weight"]
            row.target_value = item["target_value"]
            row.unit = item["unit"]
            row.remark = item.get("remark")
    db.commit()


def _ratio_pct(num: float, den: float) -> float:
    if den <= 0:
        return 100.0
    return min(100.0, max(0.0, (num / den) * 100.0))


def _month_range(year_month: str) -> tuple[date, date]:
    y, m = int(year_month[:4]), int(year_month[5:7])
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)
    return start, end


def _calc_staffing_rate(db: Session, year_month: str) -> tuple[float, float, str]:
    plans = db.query(HeadcountPlan).filter(HeadcountPlan.year_month == year_month).all()
    if not plans:
        active = db.query(func.count(Employee.id)).filter(Employee.status == "active").scalar() or 0
        return float(active), min(100.0, float(active) * 10), f"无编制计划，按在职人数={active}占位"
    planned = sum(p.planned_count for p in plans) or 0
    actual = sum(p.actual_count for p in plans) or 0
    raw = (actual / planned) if planned else 0.0
    score = min(100.0, raw * 100.0)
    return raw, score, f"actual={actual}/planned={planned}"


def _calc_recruiting(db: Session, year_month: str) -> tuple[float, float, str]:
    done_status = {"onboarding", "contract", "trained", "granted", "closed"}
    q = db.query(RecruitingReq)
    total = q.count()
    if total == 0:
        return 0.0, 100.0, "无招聘单，按满分占位"
    done = q.filter(RecruitingReq.status.in_(done_status)).count()
    score = _ratio_pct(done, total)
    return float(done), score, f"闭环={done}/{total}"


def _calc_turnover(db: Session, year_month: str) -> tuple[float, float, str]:
    start, end = _month_range(year_month)
    active = db.query(func.count(Employee.id)).filter(Employee.status == "active").scalar() or 0
    left = (
        db.query(func.count(Employee.id))
        .filter(
            Employee.status.in_(("leave", "resigned", "left")),
        )
        .scalar()
        or 0
    )
    left_month = (
        db.query(func.count(Employee.id))
        .filter(Employee.leave_date.isnot(None), Employee.leave_date >= start, Employee.leave_date < end)
        .scalar()
        or 0
    )
    den = active + left
    score = _ratio_pct(active, den) if den else 100.0
    return float(left_month), score, f"在职={active} 离职累计={left} 本月离职={left_month}"


def _calc_position_library(db: Session, year_month: str) -> tuple[float, float, str]:
    total = db.query(func.count(Position.id)).scalar() or 0
    if total == 0:
        return 0.0, 100.0, "无岗位，按满分占位"
    with_clause = (
        db.query(func.count(func.distinct(PositionClause.position_id))).scalar() or 0
    )
    score = _ratio_pct(with_clause, total)
    return float(with_clause), score, f"有条款岗位={with_clause}/{total}"


def _calc_position_first(db: Session, year_month: str) -> tuple[float, float, str]:
    ons = db.query(Onboarding).all()
    if ons:
        ok = 0
        for o in ons:
            emp = db.get(Employee, o.employee_id)
            if emp and emp.position_id:
                ok += 1
        score = _ratio_pct(ok, len(ons))
        return float(ok), score, f"入职已定岗={ok}/{len(ons)}"
    total = db.query(func.count(Employee.id)).scalar() or 0
    assigned = (
        db.query(func.count(Employee.id)).filter(Employee.position_id.isnot(None)).scalar() or 0
    )
    score = _ratio_pct(assigned, total)
    return float(assigned), score, f"员工已定岗={assigned}/{total}"


def _calc_contracts(db: Session, year_month: str) -> tuple[float, float, str]:
    active_emps = db.query(Employee).filter(Employee.status == "active").all()
    if not active_emps:
        return 0.0, 100.0, "无在职员工，按满分占位"
    covered = 0
    for emp in active_emps:
        c = (
            db.query(Contract)
            .filter(Contract.employee_id == emp.id, Contract.status == "active")
            .first()
        )
        if c:
            covered += 1
    score = _ratio_pct(covered, len(active_emps))
    return float(covered), score, f"在职有合同={covered}/{len(active_emps)}"


def _calc_training_fails(db: Session, year_month: str | None = None) -> tuple[float, float, str]:
    raw = db.query(func.count(Training.id)).filter(Training.status == "failed").scalar() or 0
    score = max(0.0, 100.0 - float(raw) * 10.0)
    return float(raw), score, f"failed_trainings={raw}"


def _calc_revoke_overtime(db: Session, year_month: str | None = None) -> tuple[float, float, str]:
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


def _calc_attendance(db: Session, year_month: str) -> tuple[float, float, str]:
    start, end = _month_range(year_month)
    open_n = (
        db.query(func.count(AttendanceException.id))
        .filter(
            AttendanceException.status == "open",
            AttendanceException.exception_date >= start,
            AttendanceException.exception_date < end,
        )
        .scalar()
        or 0
    )
    score = max(0.0, 100.0 - float(open_n) * 10.0)
    return float(open_n), score, f"当月open异常={open_n}"


def _calc_publish(db: Session, year_month: str) -> tuple[float, float, str]:
    active_pos = db.query(Position).filter(Position.status == "active").all()
    if not active_pos:
        return 0.0, 100.0, "无在用岗位，按满分占位"
    published = sum(1 for p in active_pos if (p.jd_summary or "").strip())
    wf_pub = (
        db.query(func.count(WorkflowDefinition.id))
        .filter(WorkflowDefinition.status == "published")
        .scalar()
        or 0
    )
    score = _ratio_pct(published, len(active_pos))
    return float(published), score, f"已发布JD岗位={published}/{len(active_pos)} 已发布流程={wf_pub}"


def _calc_mapping(db: Session, year_month: str) -> tuple[float, float, str]:
    present = {
        m.kpi_code
        for m in db.query(ScorecardMapping).filter(ScorecardMapping.kpi_code.in_(V22_CODES)).all()
    }
    expected = len(V22_CODES)
    got = len(present)
    score = _ratio_pct(got, expected)
    return float(got), score, f"T11覆盖 V2.2 条款={got}/{expected}"


def _calc_r2_access(db: Session, year_month: str) -> tuple[float, float, str]:
    media = db.query(Employee).filter(Employee.is_media_contact.is_(True)).all()
    if not media:
        return 0.0, 100.0, "无媒体联络人，按满分占位"
    today = date.today()
    ok = 0
    for emp in media:
        row = (
            db.query(Training)
            .filter(
                Training.employee_id == emp.id,
                Training.course_code == "wipe_r2",
                Training.status == "passed",
                Training.valid_until.isnot(None),
                Training.valid_until >= today,
            )
            .first()
        )
        if row:
            ok += 1
    score = _ratio_pct(ok, len(media))
    return float(ok), score, f"媒体联络人有效wipe_r2={ok}/{len(media)}"


def _calc_iso(db: Session, year_month: str) -> tuple[float, float, str]:
    rows = db.query(Evidence).all()
    iso_n = 0
    for e in rows:
        blob = f"{e.ref_type or ''} {e.title or ''} {e.content or ''}".lower()
        if "iso" in blob:
            iso_n += 1
    if iso_n > 0:
        return float(iso_n), 100.0, f"ISO证据={iso_n}条"
    # 无 ISO 字样时：有任意证据给 60 占位，否则 0
    if rows:
        return 0.0, 60.0, f"有证据{len(rows)}条但无ISO标识，占位60分"
    return 0.0, 0.0, "无ISO证据"


CALCULATORS = {
    "3.1": _calc_staffing_rate,
    "3.2": _calc_recruiting,
    "3.3": _calc_turnover,
    "3.4": _calc_position_library,
    "3.5": _calc_position_first,
    "3.6": _calc_contracts,
    "3.7": _calc_training_fails,
    "3.8": _calc_revoke_overtime,
    "3.9": _calc_attendance,
    "3.10": _calc_publish,
    "3.11": _calc_mapping,
    "3.12": _calc_r2_access,
    "3.13": _calc_iso,
    # 兼容旧计算器名（若外部仍引用）
    "staffing_rate": _calc_staffing_rate,
    "training_fail_count": _calc_training_fails,
    "revoke_overtime_count": _calc_revoke_overtime,
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

    db.query(HrManagerScore).filter(HrManagerScore.year_month == year_month).delete()
    db.commit()

    mappings = (
        db.query(ScorecardMapping)
        .filter(ScorecardMapping.kpi_code.in_(V22_CODES))
        .all()
    )
    order = {code: i for i, code in enumerate(V22_CODES)}
    mappings.sort(key=lambda m: order.get(m.kpi_code, 99))

    scores: list[HrManagerScore] = []
    total_weighted = 0.0

    for m in mappings:
        calc = CALCULATORS.get(m.kpi_code)
        if calc:
            raw, score, detail = calc(db, year_month)
        else:
            raw, score, detail = 0.0, 0.0, "无计算器，占位0分"
        weight = m.weight or 0.0
        # V2.2 权重为百分制分值（如到岗12），weighted = 条款得分×权重/100
        weighted = score * weight / 100.0
        total_weighted += weighted
        row = HrManagerScore(
            year_month=year_month,
            kpi_code=m.kpi_code,
            kpi_name=m.kpi_name,
            raw_value=raw,
            score=score,
            weight=weight,
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
