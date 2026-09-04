"""CINO HR API — FastAPI entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.seed import seed
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
    workflows,
)
from app.routers import auth_router, sys_rbac, files, notifications


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    try:
        seed()
    except Exception as e:  # noqa: BLE001
        print(f"Seed warning: {e}")
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "CINO 回收公司人事微服务。"
        "鉴权：登录 Bearer token 或请求头 X-API-Key（默认 demo-key）。"
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

app.include_router(auth_router.router)
app.include_router(sys_rbac.router)
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
app.include_router(workflows.router)
app.include_router(files.router)
app.include_router(notifications.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "cino-hr-api", "version": settings.app_version}
