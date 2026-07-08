"""
routes/insight.py — POST /insight
RAG + Claude narrative generation endpoint.
"""

import logging
import os
import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.schemas import InsightRequest, InsightResponse
from db import get_db, engine as db_engine
from cache import insight_cache, make_cache_key, is_cache_enabled
from rag_engine import generate_risk_narrative

log = logging.getLogger(__name__)
router = APIRouter(prefix="/insight", tags=["insight"])

_anthropic_client: anthropic.Anthropic | None = None

def get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set.")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


@router.post("", response_model=InsightResponse)
def get_insight(req: InsightRequest, db: Session = Depends(get_db)):
    """
    Generate a grounded credit risk narrative for a company + analyst question.
    Responses are cached (insight_cache) when CACHE_ENABLED=true.
    """
    cache_key = make_cache_key("insight", req.company_id, req.query)
    if is_cache_enabled() and cache_key in insight_cache:
        cached = insight_cache[cache_key]
        cached["response_time_ms"] = 0.5   # mark as cache hit
        return InsightResponse(**cached)

    # ── Fetch company + risk score ────────────────────────────────────────────
    row = db.execute(text("""
        SELECT c.id::text, c.ticker, rs.altman_z, rs.altman_tier,
               rs.distance_to_default, rs.prob_of_default,
               rs.composite_risk_score, rs.risk_tier, rs.top_risk_driver_1
        FROM companies c
        LEFT JOIN LATERAL (
            SELECT * FROM risk_scores WHERE company_id = c.id
            ORDER BY period DESC LIMIT 1
        ) rs ON TRUE
        WHERE c.id::text = :cid OR c.ticker = :cid
    """), {"cid": req.company_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Company '{req.company_id}' not found.")

    company_id, ticker = row[0], row[1]
    risk_score_row = {
        "altman_z":             row[2],
        "altman_tier":          row[3],
        "distance_to_default":  row[4],
        "prob_of_default":      row[5],
        "composite_risk_score": row[6],
        "risk_tier":            row[7],
        "top_risk_driver_1":    row[8],
    }

    # ── Generate narrative ────────────────────────────────────────────────────
    try:
        narrative, recommendation, sources_used, elapsed_ms = generate_risk_narrative(
            company_id     = company_id,
            ticker         = ticker,
            query          = req.query,
            risk_score_row = risk_score_row,
            db_engine      = db_engine,
            anthropic_client = get_anthropic(),
        )
    except Exception as exc:
        log.error(f"Narrative generation failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Narrative generation failed: {str(exc)}")

    result = {
        "company_id":       company_id,
        "ticker":           ticker,
        "query":            req.query,
        "narrative":        narrative,
        "recommendation":   recommendation,
        "sources_used":     sources_used,
        "response_time_ms": elapsed_ms,
    }

    if is_cache_enabled():
        insight_cache[cache_key] = result

    return InsightResponse(**result)
