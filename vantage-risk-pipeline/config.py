"""
config.py — centralised configuration loader.
Reads Supabase Postgres connection string from .env and exposes
a ready-to-use SQLAlchemy engine.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env from the project root (one level up from this file if nested)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise EnvironmentError(
        "DATABASE_URL is not set. "
        "Copy .env.example → .env and paste your Supabase Postgres connection string."
    )

# Supabase requires sslmode=require; add it if not already present
if "sslmode" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # detect stale connections
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── Risk engine knobs ─────────────────────────────────────────────────────────
RISK_FREE_RATE: float = float(os.getenv("RISK_FREE_RATE", "0.053"))  # 5.3% US 10yr approx
DTD_TIME_HORIZON: float = float(os.getenv("DTD_TIME_HORIZON", "1.0"))  # 1-year horizon

# ── Sentence-Transformers ────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM: int = 384  # fixed for all-MiniLM-L6-v2

# ── RAG ───────────────────────────────────────────────────────────────────────
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
CHUNK_SIZE_TOKENS: int = int(os.getenv("CHUNK_SIZE_TOKENS", "500"))


def test_connection() -> bool:
    """Quick health-check — returns True if Supabase is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"[config] DB connection failed: {exc}")
        return False


if __name__ == "__main__":
    ok = test_connection()
    print("✅ DB connected" if ok else "❌ DB connection failed — check .env")
