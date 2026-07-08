"""
routes/scenario.py — POST /scenario
Rate-shock stress test: simulates the effect of a rate increase on a company.
"""

import sys
from pathlib import Path
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vantage-risk-pipeline"))

from models.schemas import ScenarioRequest, ScenarioResponse
from db import get_db
from risk_engine import altman_z_score

log = logging.getLogger(__name__)
router = APIRouter(prefix="/scenario", tags=["scenario"])


@router.post("", response_model=ScenarioResponse)
def run_scenario(req: ScenarioRequest, db: Session = Depends(get_db)):
    """
    Simulate the effect of a rate shock on a company's credit risk.

    Mechanism:
    1. Fetch latest financials and risk score for the company.
    2. Apply the rate shock: increase in interest expense = existing_debt × (bps/10000).
    3. Recompute EBIT under stress (EBIT_stressed = EBIT_base - extra_interest_expense).
    4. Rerun Altman Z-Score with the stressed EBIT.
    5. Return base vs stressed comparison.
    """
    row = db.execute(text("""
        SELECT
            c.id::text, c.ticker,
            f.ebit, f.long_term_debt, f.total_assets, f.total_liabilities,
            f.working_capital, f.retained_earnings, f.market_cap, f.revenue,
            f.interest_expense, f.interest_coverage,
            rs.altman_z, rs.altman_tier
        FROM companies c
        LEFT JOIN LATERAL (
            SELECT * FROM financials WHERE company_id = c.id
            ORDER BY period DESC LIMIT 1
        ) f ON TRUE
        LEFT JOIN LATERAL (
            SELECT altman_z, altman_tier FROM risk_scores WHERE company_id = c.id
            ORDER BY period DESC LIMIT 1
        ) rs ON TRUE
        WHERE c.id::text = :cid OR c.ticker = :cid
    """), {"cid": req.company_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Company '{req.company_id}' not found.")

    (company_id, ticker,
     ebit, long_term_debt, total_assets, total_liabilities,
     working_capital, retained_earnings, market_cap, revenue,
     interest_expense, interest_coverage,
     base_altman_z, base_tier) = row

    # ── Rate shock mechanics ─────────────────────────────────────────────────
    # Additional annual interest cost = total_liabilities × (bps / 10000)
    shock_rate   = (req.rate_shock_bps / 10_000)
    debt_balance = float(long_term_debt or total_liabilities or 0)
    extra_interest = debt_balance * shock_rate

    ebit_stressed        = (float(ebit or 0)) - extra_interest
    ta                   = float(total_assets or 1)
    tl                   = float(total_liabilities or 1)
    ic_stressed          = (
        round(ebit_stressed / abs(float(interest_expense or 1)), 4)
        if interest_expense else None
    )

    # ── Recompute Altman Z under stress ──────────────────────────────────────
    try:
        stressed = altman_z_score(
            working_capital     = float(working_capital or 0),
            retained_earnings   = float(retained_earnings or 0),
            ebit                = ebit_stressed,
            market_value_equity = float(market_cap or 0),
            sales               = float(revenue or 0),
            total_assets        = ta,
            total_liabilities   = tl,
        )
        stressed_z    = stressed.z_score
        stressed_tier = stressed.tier
    except Exception as exc:
        log.warning(f"Scenario Altman failed: {exc}")
        stressed_z    = None
        stressed_tier = None

    # ── Plain-language narrative ──────────────────────────────────────────────
    direction = "increase" if req.rate_shock_bps > 0 else "decrease"
    narrative = (
        f"A {abs(req.rate_shock_bps)}bps rate {direction} adds approximately "
        f"${extra_interest/1e6:.1f}M in annual interest expense for {ticker}. "
    )
    if stressed_z is not None and base_altman_z is not None:
        delta = stressed_z - float(base_altman_z)
        narrative += (
            f"Altman Z-Score shifts from {base_altman_z:.2f} to {stressed_z:.2f} "
            f"({delta:+.2f}), "
        )
        if stressed_tier != base_tier:
            narrative += f"moving the risk classification from '{base_tier}' to '{stressed_tier}'."
        else:
            narrative += f"remaining in the '{stressed_tier}' tier."
    else:
        narrative += "Insufficient data to compute full stressed Z-Score."

    return ScenarioResponse(
        company_id              = company_id,
        ticker                  = ticker,
        rate_shock_bps          = req.rate_shock_bps,
        base_altman_z           = float(base_altman_z) if base_altman_z else None,
        stressed_altman_z       = stressed_z,
        base_tier               = base_tier,
        stressed_tier           = stressed_tier,
        base_interest_coverage  = float(interest_coverage) if interest_coverage else None,
        stressed_interest_coverage = ic_stressed,
        tier_changed            = (stressed_tier != base_tier) and stressed_tier is not None,
        narrative               = narrative,
    )
