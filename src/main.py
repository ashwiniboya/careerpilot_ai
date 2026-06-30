"""
main.py — FastAPI application entry-point for CareerPilot AI.

Starts the FastAPI server with:
  - CORS middleware (configured for local development and production)
  - JWT authentication routes
  - Dashboard data routes
  - SSE streaming chat and WebSocket interview routes
  - Static file serving for the glassmorphic SPA frontend
  - Startup: database initialisation and health checks
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from src.api.auth import router as auth_router
from src.api.chat import router as chat_router
from src.api.dashboard import router as dashboard_router
from src.monitoring.logger import _configure_logger

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
_configure_logger()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CareerPilot AI",
    description=(
        "Autonomous multi-agent career co-pilot. "
        "Powered by Google ADK + Gemini 2.5 Pro/Flash."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(chat_router)

# ---------------------------------------------------------------------------
# Static files (SPA frontend)
# ---------------------------------------------------------------------------

FRONTEND_DIR = ROOT / "src" / "frontend"

if FRONTEND_DIR.exists():
    # Mount /static for CSS/JS assets
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_spa():
        """Serve the SPA shell — all routing handled client-side."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_fallback(full_path: str):
        """Catch-all: redirect unknown paths to SPA for client-side routing."""
        index = FRONTEND_DIR / "index.html"
        return FileResponse(str(index))

# ---------------------------------------------------------------------------
# Startup / shutdown events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    logger.info("CareerPilot AI starting up…")
    # Initialise database tables
    try:
        from database.init_db import init_db
        init_db()
        logger.info("Database initialised successfully.")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

    # Verify API key presence (non-fatal — offline mode still works)
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY not set. LLM features will run in offline/stub mode. "
            "Set the key in .env to enable full AI capabilities."
        )
    else:
        logger.info("GEMINI_API_KEY detected. AI features are enabled.")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("CareerPilot AI shutting down.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health_check():
    """Simple liveness probe for Docker/k8s."""
    return {"status": "ok", "service": "careerpilot-ai"}


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("ENV", "development").lower() == "development"
    logger.info(f"Starting CareerPilot AI on {host}:{port} (reload={reload})")
    uvicorn.run("src.main:app", host=host, port=port, reload=reload)
