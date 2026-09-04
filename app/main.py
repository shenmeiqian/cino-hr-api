"""CINO HR API — FastAPI entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import (
    attendance,
    contracts,
    employees,
    evidences,
    headcounts,
    kpi,
    onboarding,
    permissions,
    positions,
    recruiting,
    tickets,
    trainings,
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "CINO 回收公司人事微服务 MVP（人事主管 KPI V2.2 字段表 T01–T15）。"
        "鉴权：请求头 X-API-Key（默认 demo-key）。"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employees.router)
app.include_router(headcounts.router)
app.include_router(positions.router)
app.include_router(recruiting.router)
app.include_router(onboarding.router)
app.include_router(contracts.router)
app.include_router(trainings.router)
app.include_router(permissions.router)
app.include_router(attendance.router)
app.include_router(kpi.router)
app.include_router(evidences.router)
app.include_router(tickets.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "cino-hr-api", "version": settings.app_version}
