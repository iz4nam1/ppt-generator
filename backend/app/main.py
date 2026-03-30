"""
main.py
=======
FastAPI application entry point.

All routes, middleware, and startup logic registered here.
Keep this file thin — it only wires things together.

FUTURE: Add background scheduler (APScheduler) for:
    - Daily credit top-ups for free users
    - Sending usage digest emails
    - Cleaning up expired temp files
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import ALLOWED_ORIGINS, SITE_NAME, DOCS_ENABLED, TEMP_DIR
from app.database import init_db
from app.middleware.usage_logger import RequestLoggerMiddleware
from app.routes import auth, generate, templates, admin, payments

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


# ── Startup / shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    init_db()

    # Clean leftover temp files from crashed previous runs
    cleaned = sum(1 for f in TEMP_DIR.glob("*.pptx")
                  if not f.unlink() or True)  # unlink returns None
    if cleaned:
        log.info(f"Startup: cleaned {cleaned} temp files")

    log.info(f"🚀 {SITE_NAME} backend is live")
    yield
    # ── Shutdown ──
    log.info("Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title       = SITE_NAME,
    version     = "2.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs"        if DOCS_ENABLED else None,
    redoc_url   = "/redoc"       if DOCS_ENABLED else None,
    openapi_url = "/openapi.json" if DOCS_ENABLED else None,
)

# ── State ─────────────────────────────────────────────────────────────────────
app.state.limiter = limiter

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware (order matters — outermost runs first) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_methods     = ["GET", "POST", "DELETE"],
    allow_headers     = ["Content-Type", "X-User-Id"],
    allow_credentials = False,
)
app.add_middleware(RequestLoggerMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(generate.router)
app.include_router(templates.router)
app.include_router(admin.router)
app.include_router(payments.router)

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host   = "0.0.0.0",
        port   = 8001,
        reload = os.getenv("ENV") == "development",
    )
