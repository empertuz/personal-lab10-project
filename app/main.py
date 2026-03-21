import logging
import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_async_connection
from app.routers import rainfall, stations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    logger.info("Starting PluvioApp, DB: %s", settings.DATABASE_PATH)
    app.state.db = await get_async_connection()
    yield
    await app.state.db.close()
    logger.info("PluvioApp shut down")


app = FastAPI(
    title="PluvioApp",
    version="0.1.0",
    description="Pluviometric Station Analysis Platform — IDEAM data",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(rainfall.router)


@app.get("/api/health", tags=["system"])
async def health(request: Request):
    db = request.app.state.db
    counts = {}
    for table in ("stations", "rainfall_daily", "rainfall_monthly", "rainfall_yearly"):
        row = await db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM {table}")  # noqa: S608
        counts[table] = row[0]["cnt"]
    return {"status": "ok", "tables": counts}


@app.post("/api/admin/ingest", tags=["system"])
async def trigger_ingest(x_admin_key: str = Header(...)):
    settings = get_settings()
    if x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    subprocess.Popen(
        [sys.executable, "scripts/ingest.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"status": "ingestion_started"}
