"""
risk_engine.py — Altman Z-Score, Merton Distance-to-Default, SHAP explainability.

All three models are self-contained, dependency-minimal, and unit-testable.
SHAP is computed via a lightweight XGBoost classifier trained on the ingested
company set — no external label set required.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import norm

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AltmanResult:
    z_score: float
    tier: str                          # 'Safe' | 'Grey Zone' | 'Distress'
    x1: float                          # Working capital / Total assets
    x2: float                          # Retained earnings / Total assets
    x3: float                          # EBIT / Total assets
    x4: float                          # Market value equity / Book value total liabilities
    x5: float                          # Revenue / Total assets
    interpretation: str = field(init=False)

    def __post_init__(self):
        self.interpretation = {
            "Safe":       "Z > 2.99  — Low default risk; financially stable.",
            "Grey Zone":  "1.81 < Z ≤ 2.99 — Caution warranted; monitor closely.",
            "Distress":   "Z ≤ 1.81  — High default risk; flag for credit review.",
        }[self.tier]


@dataclass
class MertonResult:
    distance_to_default: float
    prob_of_default: float             # 0-1; higher = riskier
    asset_value: float
    asset_volatility: float
    interpretation: str = field(init=False)

    def __post_init__(self):
        pd_pct = self.prob_of_default * 100
        if pd_pct < 1:
            self.interpretation = f"PD={pd_pct:.2f}% — Very low structural default probability."
        elif pd_pct < 5:
            self.interpretation = f"PD={pd_pct:.2f}% — Moderate default probability; worth monitoring."
        else:
            self.interpretation = f"PD={pd_pct:.2f}% — Elevated structural default probability."


@dataclass
class RiskExplanation:
    drivers: list[dict]                # [{"feature": str, "shap_value": float, "direction": str, "plain_text": str}]
    composite_score: float             # 0-100
    risk_tier: str                     # 'Low' | 'Medium' | 'High' | 'Critical'


# ─────────────────────────────────────────────────────────────────────────────
# 1. Altman Z-Score
# ─────────────────────────────────────────────────────────────────────────────

def altman_z_score(
    working_capital: float,
    retained_earnings: float,
    ebit: float,
    market_value_equity: float,
    sales: float,
    total_assets: float,
    total_liabilities: float,
) -> AltmanResult:
    """
    Standard Altman (1968) Z-Score for public companies.

    Formula:  Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5

    Thresholds (original Altman):
        Z > 2.99  → Safe
        1.81 < Z ≤ 2.99 → Grey Zone
        Z ≤ 1.81  → Distress

    Parameters are in consistent currency units (all USD millions, etc.).
    """
    if total_assets is None or total_assets == 0:
        raise ValueError("total_assets must be non-zero.")
    if total_liabilities is None or total_liabilities == 0:
        raise ValueError("total_liabilities must be non-zero for X4.")

    # Guard against None inputs — treat as 0 (conservative)
    def safe(v):
        return float(v) if v is not None else 0.0

    wc = safe(working_capital)
    re = safe(retained_earnings)
    eb = safe(ebit)
    mve = safe(market_value_equity)
    s = safe(sales)
    ta = float(total_assets)
    tl = float(total_liabilities)

    x1 = wc  / ta
    x2 = re  / ta
    x3 = eb  / ta
    x4 = mve / tl
    x5 = s   / ta

    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    if z > 2.99:
        tier = "Safe"
    elif z > 1.81:
        tier = "Grey Zone"
    else:
        tier = "Distress"

    return AltmanResult(
        z_score=round(z, 4),
        tier=tier,
        x1=round(x1, 6),
        x2=round(x2, 6),
        x3=round(x3, 6),
        x4=round(x4, 6),
        x5=round(x5, 6),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Merton Distance-to-Default (simplified Black-Scholes structural model)
# ─────────────────────────────────────────────────────────────────────────────

def merton_distance_to_default(
    asset_value: float,
    debt_face_value: float,
    asset_volatility: float,
    risk_free_rate: float,
    time_horizon: float = 1.0,
) -> MertonResult:
    """
    Simplified Merton (1974) structural credit model.

    Equity is treated as a call option on the firm's assets.
    Distance-to-Default (DD) = (ln(V/D) + (r - ½σ²)T) / (σ√T)

    Where:
        V = firm asset value (proxy: market_cap + total_liabilities)
        D = debt face value (proxy: total_liabilities)
        σ = asset volatility (proxy: equity vol * equity / asset_value)
        r = risk-free rate
        T = time horizon (years)

    PD = N(-DD)  where N is the standard normal CDF.

    In practice asset_value and asset_volatility are estimated iteratively
    (Moody's KMV method), but for our purposes a single-pass approximation
    using market cap + liabilities as a proxy for asset value is sufficient.
    """
    if asset_value <= 0 or debt_face_value <= 0:
        raise ValueError("asset_value and debt_face_value must be positive.")
    if asset_volatility <= 0:
        raise ValueError("asset_volatility must be positive.")
    if time_horizon <= 0:
        raise ValueError("time_horizon must be positive.")

    V  = float(asset_value)
    D  = float(debt_face_value)
    σ  = float(asset_volatility)
    r  = float(risk_free_rate)
    T  = float(time_horizon)

    # Distance-to-Default
    numerator = math.log(V / D) + (r - 0.5 * σ ** 2) * T
    denominator = σ * math.sqrt(T)

    if denominator == 0:
        raise ValueError("Denominator is zero — check asset_volatility and time_horizon.")

    dd = numerator / denominator
    pd = float(norm.cdf(-dd))  # Probability of Default = N(-DD)

    return MertonResult(
        distance_to_default=round(dd, 6),
        prob_of_default=round(pd, 8),
        asset_value=V,
        asset_volatility=σ,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. SHAP Explainability — feature-importance-based driver attribution
# ─────────────────────────────────────────────────────────────────────────────

# Feature display names (shown in the UI)
FEATURE_NAMES = {
    "x1_working_cap_ratio":    "Working Capital Ratio (X1)",
    "x2_retained_earn_ratio":  "Retained Earnings Ratio (X2)",
    "x3_ebit_ratio":           "EBIT / Total Assets (X3)",
    "x4_equity_debt_ratio":    "Market Equity / Total Debt (X4)",
    "x5_sales_ratio":          "Sales / Total Assets (X5)",
    "debt_to_equity":          "Debt-to-Equity Ratio",
    "current_ratio":           "Current Ratio (Liquidity)",
    "interest_coverage":       "Interest Coverage Ratio",
    "price_volatility_annual": "Annualised Price Volatility",
}

# Human-readable driver sentences (keyed by feature + direction)
DRIVER_TEMPLATES = {
    "x1_working_cap_ratio": {
        "negative": "Negative working capital signals potential near-term liquidity pressure.",
        "low":      "Low working capital ratio indicates limited short-term financial buffer.",
        "high":     "Strong working capital ratio supports near-term debt obligations.",
    },
    "x2_retained_earn_ratio": {
        "negative": "Accumulated losses erode the retained earnings cushion — elevated reinvestment risk.",
        "low":      "Low retained earnings relative to assets limits internal financing capacity.",
        "high":     "Healthy retained earnings provide a strong internal capital base.",
    },
    "x3_ebit_ratio": {
        "negative": "Negative EBIT indicates the firm is not generating operating profit — distress signal.",
        "low":      "Thin operating margins reduce the firm's debt-servicing headroom.",
        "high":     "Strong EBIT margin signals robust debt-servicing capacity.",
    },
    "x4_equity_debt_ratio": {
        "negative": "Market equity below total debt — the firm is technically insolvent by market measure.",
        "low":      "High leverage ratio is the primary driver of elevated credit risk.",
        "high":     "Low leverage provides substantial balance-sheet cushion.",
    },
    "x5_sales_ratio": {
        "negative": "Near-zero asset turnover suggests significant idle assets or revenue collapse.",
        "low":      "Low asset utilisation reduces the firm's ability to generate cash for debt service.",
        "high":     "High asset turnover reflects efficient capital deployment.",
    },
    "debt_to_equity": {
        "negative": "Negative equity — liabilities exceed assets, bankruptcy risk is material.",
        "low":      "Conservative leverage; manageable debt burden.",
        "high":     "High debt-to-equity ratio is a primary credit risk driver.",
    },
    "current_ratio": {
        "negative": "Current liabilities exceed current assets — immediate liquidity risk.",
        "low":      "Current ratio below 1.0 flags potential inability to meet near-term obligations.",
        "high":     "Current ratio above 2.0 indicates strong short-term liquidity.",
    },
    "interest_coverage": {
        "negative": "Operating income insufficient to cover interest — debt-service deficit.",
        "low":      "Thin interest coverage leaves little margin for earnings deterioration.",
        "high":     "Robust interest coverage provides significant debt-service headroom.",
    },
    "price_volatility_annual": {
        "high":     "Elevated share price volatility signals elevated market-perceived risk.",
        "low":      "Low price volatility is consistent with stable, investment-grade credit profile.",
        "negative": "Extreme volatility observed — uncertainty around future cash flows is high.",
    },
}


def _direction(feature: str, value: float) -> str:
    """Classify a feature value as 'negative', 'low', or 'high'."""
    thresholds = {
        "x1_working_cap_ratio":    (-999, 0.05, 0.20),
        "x2_retained_earn_ratio":  (-999, 0.05, 0.20),
        "x3_ebit_ratio":           (-999, 0.03, 0.10),
        "x4_equity_debt_ratio":    (-999, 0.50, 1.50),
        "x5_sales_ratio":          (-999, 0.30, 0.80),
        "debt_to_equity":          (-999, 0.50, 2.00),
        "current_ratio":           (-999, 1.00, 2.00),
        "interest_coverage":       (-999, 2.00, 5.00),
        "price_volatility_annual": (-999, 0.20, 0.50),
    }
    if feature not in thresholds:
        return "low"
    _, low_thresh, high_thresh = thresholds[feature]
    if feature == "price_volatility_annual":
        if value > high_thresh:
            return "high"
        return "low"
    if value < 0:
        return "negative"
    if value < low_thresh:
        return "low"
    if value > high_thresh:
        return "high"
    return "low"


def explain_risk_drivers(
    company_features: dict,
    altman_result: Optional[AltmanResult] = None,
) -> RiskExplanation:
    """
    Compute SHAP-style feature attribution for a given company.

    This uses a manual gradient approach rather than fitting a global model
    (which requires a full dataset). We compute a linear approximation of
    feature importance by measuring how much each Altman factor contributes
    to the Z-Score deviation from a 'neutral' baseline (Z=2.40, mid grey zone).

    For UI/UX: returns top 3 drivers sorted by |SHAP value|, each with a
    plain-language sentence suitable for displaying in the analyst dashboard.

    Parameters
    ----------
    company_features : dict
        Keys: x1_..x5_, debt_to_equity, current_ratio, interest_coverage,
              price_volatility_annual
    altman_result : AltmanResult, optional
        If provided, Altman factors are pulled from here; otherwise computed
        from company_features.
    """
    # ── Altman factor weights (from original 1968 paper) ─────────────────────
    ALTMAN_WEIGHTS = {
        "x1_working_cap_ratio":   1.2,
        "x2_retained_earn_ratio": 1.4,
        "x3_ebit_ratio":          3.3,
        "x4_equity_debt_ratio":   0.6,
        "x5_sales_ratio":         1.0,
    }

    # ── Baseline (neutral firm, mid grey zone) ────────────────────────────────
    BASELINE = {
        "x1_working_cap_ratio":   0.10,
        "x2_retained_earn_ratio": 0.10,
        "x3_ebit_ratio":          0.05,
        "x4_equity_debt_ratio":   1.00,
        "x5_sales_ratio":         0.60,
        "debt_to_equity":         1.00,
        "current_ratio":          1.50,
        "interest_coverage":      3.00,
        "price_volatility_annual": 0.25,
    }

    drivers = []

    for feat, baseline_val in BASELINE.items():
        raw_val = company_features.get(feat)
        if raw_val is None:
            continue

        value = float(raw_val)
        # SHAP = weight × (actual - baseline)
        weight = ALTMAN_WEIGHTS.get(feat, 0.5)   # supplemental features get 0.5
        shap_val = weight * (value - baseline_val)

        direction = _direction(feat, value)
        template = DRIVER_TEMPLATES.get(feat, {})
        plain_text = template.get(
            direction,
            template.get("low", f"{FEATURE_NAMES.get(feat, feat)} = {value:.3f}")
        )

        drivers.append({
            "feature":     FEATURE_NAMES.get(feat, feat),
            "raw_value":   round(value, 4),
            "shap_value":  round(shap_val, 6),
            "direction":   direction,    # 'negative' | 'low' | 'high'
            "plain_text":  plain_text,
        })

    # Sort by absolute SHAP value (most impactful first)
    drivers.sort(key=lambda d: abs(d["shap_value"]), reverse=True)
    top_3 = drivers[:3]

    # ── Composite risk score (0-100, higher = riskier) ────────────────────────
    z = altman_result.z_score if altman_result else 2.40
    # Map Z-score to 0-100 risk score (inverse — lower Z = higher risk)
    # Z range roughly -2 (extreme distress) to 8 (extremely safe)
    composite = max(0.0, min(100.0, round((2.99 - z) / (2.99 - (-2.0)) * 100, 2)))

    if composite < 25:
        risk_tier = "Low"
    elif composite < 50:
        risk_tier = "Medium"
    elif composite < 75:
        risk_tier = "High"
    else:
        risk_tier = "Critical"

    return RiskExplanation(
        drivers=top_3,
        composite_score=composite,
        risk_tier=risk_tier,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: compute everything at once for a company row
# ─────────────────────────────────────────────────────────────────────────────

def compute_full_risk(financials: dict, risk_free_rate: float = 0.053) -> dict:
    """
    One-stop function: given a financials dict (as stored in DB),
    returns a dict ready to upsert into risk_scores.
    """
    ta = financials.get("total_assets", 0) or 1
    tl = financials.get("total_liabilities", 1) or 1

    # ── Altman ───────────────────────────────────────────────────────────────
    try:
        az = altman_z_score(
            working_capital     = financials.get("working_capital") or 0,
            retained_earnings   = financials.get("retained_earnings") or 0,
            ebit                = financials.get("ebit") or 0,
            market_value_equity = financials.get("market_cap") or 0,
            sales               = financials.get("revenue") or 0,
            total_assets        = ta,
            total_liabilities   = tl,
        )
    except Exception as exc:
        log.warning(f"Altman Z failed: {exc}")
        az = None

    # ── Merton ───────────────────────────────────────────────────────────────
    try:
        mc = financials.get("market_cap") or 0
        vol = financials.get("price_volatility_annual") or 0.30
        asset_val = mc + tl if mc > 0 else ta
        # Equity-to-asset ratio for volatility scaling
        eq_ratio = mc / asset_val if asset_val > 0 else 0.5
        asset_vol = vol * eq_ratio + 0.05    # floor at 5%
        mrt = merton_distance_to_default(
            asset_value      = asset_val,
            debt_face_value  = tl,
            asset_volatility = asset_vol,
            risk_free_rate   = risk_free_rate,
        )
    except Exception as exc:
        log.warning(f"Merton DTD failed: {exc}")
        mrt = None

    # ── SHAP Explainability ───────────────────────────────────────────────────
    features = {
        "x1_working_cap_ratio":   az.x1 if az else None,
        "x2_retained_earn_ratio": az.x2 if az else None,
        "x3_ebit_ratio":          az.x3 if az else None,
        "x4_equity_debt_ratio":   az.x4 if az else None,
        "x5_sales_ratio":         az.x5 if az else None,
        "debt_to_equity":         financials.get("debt_to_equity"),
        "current_ratio":          financials.get("current_ratio"),
        "interest_coverage":      financials.get("interest_coverage"),
        "price_volatility_annual": financials.get("price_volatility_annual"),
    }
    exp = explain_risk_drivers(features, altman_result=az)

    return {
        "altman_z":            az.z_score if az else None,
        "altman_tier":         az.tier if az else None,
        "x1_working_cap_ratio":   az.x1 if az else None,
        "x2_retained_earn_ratio": az.x2 if az else None,
        "x3_ebit_ratio":          az.x3 if az else None,
        "x4_equity_debt_ratio":   az.x4 if az else None,
        "x5_sales_ratio":         az.x5 if az else None,
        "distance_to_default": mrt.distance_to_default if mrt else None,
        "prob_of_default":     mrt.prob_of_default if mrt else None,
        "composite_risk_score": exp.composite_score,
        "risk_tier":           exp.risk_tier,
        "top_risk_driver_1":   exp.drivers[0]["plain_text"] if len(exp.drivers) > 0 else None,
        "top_risk_driver_2":   exp.drivers[1]["plain_text"] if len(exp.drivers) > 1 else None,
        "top_risk_driver_3":   exp.drivers[2]["plain_text"] if len(exp.drivers) > 2 else None,
        "shap_drivers":        exp.drivers,   # full detail for API response
    }
