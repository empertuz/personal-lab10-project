import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# Serve frontend static files in production
_static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _static_dir.is_dir():
    from starlette.responses import FileResponse

    # Mount assets (JS/CSS/images) under /assets
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

    # Serve favicon
    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        return FileResponse(_static_dir / "favicon.svg")

    # SPA fallback: serve index.html for all non-API routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(_static_dir / "index.html")


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
