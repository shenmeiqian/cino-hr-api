from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_perm, require_user_or_api_key
from app.database import get_db
from app.models.performance import HrManagerScore, PerformanceBatch, ScorecardMapping
from app.schemas.performance import (
    HrManagerScoreOut,
    KpiRunResult,
    PerformanceBatchCreate,
    PerformanceBatchOut,
    ScorecardMappingCreate,
    ScorecardMappingOut,
)
from app.services.kpi_service import ensure_default_mappings, run_kpi_batch

router = APIRouter(prefix="/api/v1", tags=["T10-T11-T15-kpi"], dependencies=[Depends(require_user_or_api_key)])


@router.post("/performance-batches", response_model=PerformanceBatchOut)
def create_batch(body: PerformanceBatchCreate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("btn.kpi.run"))):
    if db.query(PerformanceBatch).filter(PerformanceBatch.year_month == body.year_month).first():
        raise HTTPException(400, detail="该月份批次已存在")
    row = PerformanceBatch(year_month=body.year_month, remark=body.remark, status="open")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/performance-batches", response_model=list[PerformanceBatchOut])
def list_batches(db: Session = Depends(get_db)):
    return db.query(PerformanceBatch).all()


@router.post("/scorecard-mappings", response_model=ScorecardMappingOut)
def create_mapping(body: ScorecardMappingCreate, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("btn.kpi.run"))):
    row = ScorecardMapping(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/scorecard-mappings", response_model=list[ScorecardMappingOut])
def list_mappings(db: Session = Depends(get_db)):
    ensure_default_mappings(db)
    return db.query(ScorecardMapping).all()


@router.post("/kpi/batch/{yyyy_mm}/run", response_model=KpiRunResult)
def run_batch(yyyy_mm: str, db: Session = Depends(get_db), _auth: AuthContext = Depends(require_perm("btn.kpi.run"))):
    """计算人事主管 KPI 占位得分写入 T15。"""
    batch, scores, total = run_kpi_batch(db, yyyy_mm)
    return KpiRunResult(
        year_month=yyyy_mm,
        batch_id=batch.id,
        scores=scores,
        total_weighted_score=total,
    )


@router.get("/kpi/scores", response_model=list[HrManagerScoreOut])
def list_scores(year_month: str | None = None, db: Session = Depends(get_db)):
    q = db.query(HrManagerScore)
    if year_month:
        q = q.filter(HrManagerScore.year_month == year_month)
    return q.all()
