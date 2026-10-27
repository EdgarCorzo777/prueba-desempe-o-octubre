import sys
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.app.config import settings
from api.app.database import db_cursor
from api.app.auth.jwt_handler import hash_password
from api.app.routers import (
    auth, kpis, events, stats, reports, stream, pipeline, quality, admin, chat, anomalies
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sismowatch.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure admin and viewer exist
    logger.info("Initializing SismoWatch API...")
    try:
        with db_cursor(as_admin=True, commit=True) as cur:
            # Seed Admin
            admin_hash = hash_password(settings.ADMIN_PASSWORD)
            cur.execute(
                """
                INSERT INTO auth.users (email, password_hash, full_name, role, is_active)
                VALUES (%s, %s, %s, 'admin', TRUE)
                ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash;
                """,
                (settings.ADMIN_EMAIL.lower().strip(), admin_hash, settings.ADMIN_NAME)
            )
            # Seed Viewer
            viewer_hash = hash_password(settings.VIEWER_PASSWORD)
            cur.execute(
                """
                INSERT INTO auth.users (email, password_hash, full_name, role, is_active)
                VALUES (%s, %s, %s, 'viewer', TRUE)
                ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash;
                """,
                (settings.VIEWER_EMAIL.lower().strip(), viewer_hash, settings.VIEWER_NAME)
            )
        logger.info("Database users verified and seeded.")
    except Exception as e:
        logger.warning(f"Could not seed users on startup (PostgreSQL might still be starting): {e}")
    
    yield
    logger.info("Shutting down SismoWatch API.")

app = FastAPI(
    title="SismoWatch Data API",
    description="API REST y de Streaming en Tiempo Real para la plataforma de Monitoreo Sísmico SismoWatch (Medallion + AI)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [orig.strip() for orig in settings.CORS_ORIGINS.split(",") if orig.strip()]
if not origins:
    origins = ["http://localhost:3000", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(auth.router, prefix="/api")
app.include_router(kpis.router)
app.include_router(events.router)
app.include_router(stats.router)
app.include_router(reports.router)
app.include_router(stream.router)
app.include_router(pipeline.router)
app.include_router(quality.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(anomalies.router)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SismoWatch API",
        "version": "1.0.0"
    }
