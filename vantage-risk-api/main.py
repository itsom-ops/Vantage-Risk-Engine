"""
main.py — Vantage Risk FastAPI application entry point.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from db import engine
from middleware.latency import LatencyMiddleware
from routes import companies, portfolio, scenario, latency, insight

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Vantage Risk API starting up…")
    try:
        from news_engine import start_news_scheduler
        start_news_scheduler(engine)
    except Exception as e:
        log.error(f"Failed to start background news scheduler: {e}")
    yield
    log.info("🛑 Vantage Risk API shutting down.")


app = FastAPI(
    title="Vantage Risk API",
    description=(
        "AI-powered credit risk intelligence platform. "
        "Endpoints: company risk scores (Altman Z + Merton DTD + SHAP), "
        "portfolio VaR/CVaR, rate-shock scenario simulation, "
        "RAG-grounded narrative generation (Claude), latency benchmarking."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "https://vantage-risk.vercel.app"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Latency Logging Middleware ────────────────────────────────────────────────
app.add_middleware(LatencyMiddleware, db_engine=engine, tag="live")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(companies.router)
app.include_router(portfolio.router)
app.include_router(scenario.router)
app.include_router(latency.router)
app.include_router(insight.router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
def health():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db_connected": db_ok, "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
