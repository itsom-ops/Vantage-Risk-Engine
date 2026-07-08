"""
routes/portfolio.py — POST /portfolio/risk
Historical simulation VaR/CVaR on a basket of companies.
"""

import logging
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from pydantic import BaseModel
from models.schemas import PortfolioRiskRequest, PortfolioRiskResponse, SentimentPortfolioResponse, StressedCompanyInfo
from db import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/risk", response_model=PortfolioRiskResponse)
def portfolio_risk(req: PortfolioRiskRequest, db: Session = Depends(get_db)):
    """
    Compute portfolio-level VaR and CVaR using historical simulation.

    Method:
    - Fetch composite_risk_score for each company (0-100, higher = riskier).
    - Treat each score as a proxy loss exposure (score/100 * 1 unit of capital).
    - Simulate 10,000 portfolio draws assuming log-normal return distribution
      parameterised by the mean and std of the composite scores.
    - Report 95th percentile VaR and CVaR (Expected Shortfall).
    """
    if not req.company_ids:
        raise HTTPException(status_code=400, detail="company_ids must not be empty.")

    placeholders = ", ".join([f":id_{i}" for i in range(len(req.company_ids))])
    params = {f"id_{i}": cid for i, cid in enumerate(req.company_ids)}

    rows = db.execute(text(f"""
        SELECT DISTINCT ON (rs.company_id)
            c.ticker,
            rs.composite_risk_score,
            rs.risk_tier,
            f.price_volatility_annual
        FROM risk_scores rs
        JOIN companies c ON c.id = rs.company_id
        LEFT JOIN LATERAL (
            SELECT price_volatility_annual FROM financials
            WHERE company_id = rs.company_id
            ORDER BY period DESC LIMIT 1
        ) f ON TRUE
        WHERE c.id::text IN ({placeholders})
           OR c.ticker IN ({placeholders})
        ORDER BY rs.company_id, rs.period DESC
    """), params).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="None of the provided company IDs were found.")

    scores = np.array([float(r[1] or 50) for r in rows])
    vols   = np.array([float(r[3] or 0.30) for r in rows])

    # ── Portfolio VaR/CVaR (historical simulation) ────────────────────────────
    # Simulate 10,000 equally-weighted portfolio returns
    n_sim = 10_000
    rng = np.random.default_rng(seed=42)   # reproducible for demo

    # Each company i contributes a random loss drawn from N(score_i/100, vol_i)
    # Portfolio loss = mean of individual losses
    sim_losses = np.mean(
        rng.normal(
            loc   = scores / 100,
            scale = vols * scores / 100,  # vol scales with score
            size  = (n_sim, len(scores))
        ),
        axis=1
    )
    sim_losses = np.clip(sim_losses, 0, 1)

    var_95  = float(np.percentile(sim_losses, 95)) * 100   # as %
    cvar_95 = float(sim_losses[sim_losses >= np.percentile(sim_losses, 95)].mean()) * 100

    # Risk distribution
    tier_counts: dict[str, int] = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    worst_ticker = None
    worst_score  = -1.0
    for r in rows:
        tier = r[2] or "Medium"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        score = float(r[1] or 0)
        if score > worst_score:
            worst_score  = score
            worst_ticker = r[0]

    return PortfolioRiskResponse(
        n_companies        = len(rows),
        var_95             = round(var_95, 2),
        cvar_95            = round(cvar_95, 2),
        avg_composite_score = round(float(scores.mean()), 2),
        worst_company_ticker = worst_ticker,
        worst_company_score  = round(worst_score, 2),
        risk_distribution  = tier_counts,
    )


class SentimentPortfolioRequest(BaseModel):
    company_ids: list[str]
    severity_multiplier: float = 1.0


@router.post("/sentiment-adjusted-risk", response_model=SentimentPortfolioResponse)
def sentiment_adjusted_portfolio_risk(req: SentimentPortfolioRequest, db: Session = Depends(get_db)):
    """
    Compute portfolio-level VaR/CVaR and compare it side-by-side with a sentiment-stressed model
    where negative news triggers score degradation and volatility shock.
    """
    if not req.company_ids:
        raise HTTPException(status_code=400, detail="company_ids must not be empty.")

    placeholders = ", ".join([f":id_{i}" for i in range(len(req.company_ids))])
    params = {f"id_{i}": cid for i, cid in enumerate(req.company_ids)}

    rows = db.execute(text(f"""
        SELECT DISTINCT ON (rs.company_id)
            c.id::text,
            c.ticker,
            rs.composite_risk_score,
            f.price_volatility_annual
        FROM risk_scores rs
        JOIN companies c ON c.id = rs.company_id
        LEFT JOIN LATERAL (
            SELECT price_volatility_annual FROM financials
            WHERE company_id = rs.company_id
            ORDER BY period DESC LIMIT 1
        ) f ON TRUE
        WHERE c.id::text IN ({placeholders})
           OR c.ticker IN ({placeholders})
        ORDER BY rs.company_id, rs.period DESC
    """), params).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="None of the provided company IDs were found.")

    from routes.companies import get_company_news
    
    scores = []
    stressed_scores = []
    vols = []
    stressed_vols = []
    
    net_sentiment_sum = 0
    stressed_list = []
    
    for r in rows:
        company_id = r[0]
        ticker = r[1]
        base_score = float(r[2] or 50.0)
        base_vol = float(r[3] or 0.30)
        
        # Get sentiment count from live get_company_news helper
        try:
            news = get_company_news(company_id, db)
            bearish_cnt = sum(1 for n in news if n.sentiment == "Bearish")
            bullish_cnt = sum(1 for n in news if n.sentiment == "Bullish")
            net_sent = bullish_cnt - bearish_cnt
        except Exception:
            net_sent = 0
            
        net_sentiment_sum += net_sent
        
        stress_penalty = 0.0
        vol_stress = 1.0
        if net_sent < 0:
            stress_penalty = abs(net_sent) * 8.0 * req.severity_multiplier
            stress_penalty = min(stress_penalty, 40.0)
            vol_stress = 1.0 + abs(net_sent) * 0.15 * req.severity_multiplier
            
        stressed_score = min(100.0, base_score + stress_penalty)
        
        scores.append(base_score)
        stressed_scores.append(stressed_score)
        vols.append(base_vol)
        stressed_vols.append(base_vol * vol_stress)
        
        stressed_list.append(StressedCompanyInfo(
            ticker=ticker,
            base_score=round(base_score, 1),
            stressed_score=round(stressed_score, 1),
            net_sentiment=net_sent,
            status="Stressed" if stress_penalty > 0 else "Stable"
        ))
        
    n_sim = 5000
    rng = np.random.default_rng(seed=42)
    
    # Base simulation
    base_losses = np.mean(
        rng.normal(loc=np.array(scores)/100, scale=np.array(vols)*(np.array(scores)/100), size=(n_sim, len(scores))),
        axis=1
    )
    base_losses = np.clip(base_losses, 0, 1)
    base_var = float(np.percentile(base_losses, 95)) * 100
    base_cvar = float(base_losses[base_losses >= np.percentile(base_losses, 95)].mean()) * 100
    
    # Stressed simulation
    stressed_losses = np.mean(
        rng.normal(loc=np.array(stressed_scores)/100, scale=np.array(stressed_vols)*(np.array(stressed_scores)/100), size=(n_sim, len(scores))),
        axis=1
    )
    stressed_losses = np.clip(stressed_losses, 0, 1)
    stressed_var = float(np.percentile(stressed_losses, 95)) * 100
    stressed_cvar = float(stressed_losses[stressed_losses >= np.percentile(stressed_losses, 95)].mean()) * 100
    
    return SentimentPortfolioResponse(
        base_var_95=round(base_var, 2),
        base_cvar_95=round(base_cvar, 2),
        sentiment_var_95=round(stressed_var, 2),
        sentiment_cvar_95=round(stressed_cvar, 2),
        net_portfolio_sentiment=net_sentiment_sum,
        stressed_companies=stressed_list
    )
