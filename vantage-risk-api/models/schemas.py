"""
models/schemas.py — Pydantic response models for all API endpoints.
"""

from __future__ import annotations
from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Shared
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    version: str = "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# Companies
# ─────────────────────────────────────────────────────────────────────────────

class CompanySummary(BaseModel):
    id: str
    ticker: str
    name: str
    sector: Optional[str]
    country: Optional[str]
    altman_z: Optional[float]
    altman_tier: Optional[str]
    composite_risk_score: Optional[float]
    risk_tier: Optional[str]
    prob_of_default: Optional[float]
    period: Optional[str]


class SHAPDriver(BaseModel):
    feature: str
    raw_value: float
    shap_value: float
    direction: str
    plain_text: str


class CompanyRiskDetail(BaseModel):
    id: str
    ticker: str
    name: str
    sector: Optional[str]
    # Altman Z
    altman_z: Optional[float]
    altman_tier: Optional[str]
    x1_working_cap_ratio: Optional[float]
    x2_retained_earn_ratio: Optional[float]
    x3_ebit_ratio: Optional[float]
    x4_equity_debt_ratio: Optional[float]
    x5_sales_ratio: Optional[float]
    # Merton
    distance_to_default: Optional[float]
    prob_of_default: Optional[float]
    # Composite
    composite_risk_score: Optional[float]
    risk_tier: Optional[str]
    # SHAP
    shap_drivers: list[SHAPDriver]
    top_risk_driver_1: Optional[str]
    top_risk_driver_2: Optional[str]
    top_risk_driver_3: Optional[str]
    # Meta
    period: Optional[str]
    computed_at: Optional[str]
    response_time_ms: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioRiskRequest(BaseModel):
    company_ids: list[str] = Field(..., min_length=1, max_length=50)


class PortfolioRiskResponse(BaseModel):
    n_companies: int
    var_95: float = Field(..., description="95th percentile Value-at-Risk (% loss)")
    cvar_95: float = Field(..., description="Conditional VaR / Expected Shortfall")
    avg_composite_score: float
    worst_company_ticker: Optional[str]
    worst_company_score: Optional[float]
    risk_distribution: dict[str, int]    # {"Low": 5, "Medium": 3, ...}


# ─────────────────────────────────────────────────────────────────────────────
# Scenario
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    company_id: str
    rate_shock_bps: int = Field(
        ..., ge=-500, le=500,
        description="Rate shock in basis points (positive = rate increase)"
    )


class ScenarioResponse(BaseModel):
    company_id: str
    ticker: str
    rate_shock_bps: int
    base_altman_z: Optional[float]
    stressed_altman_z: Optional[float]
    base_tier: Optional[str]
    stressed_tier: Optional[str]
    base_interest_coverage: Optional[float]
    stressed_interest_coverage: Optional[float]
    tier_changed: bool
    narrative: str


# ─────────────────────────────────────────────────────────────────────────────
# Insight / RAG
# ─────────────────────────────────────────────────────────────────────────────

class InsightRequest(BaseModel):
    company_id: str
    query: str = Field(..., min_length=5, max_length=500)


class InsightResponse(BaseModel):
    company_id: str
    ticker: str
    query: str
    narrative: str
    recommendation: str    # 'Monitor' | 'Flag for review' | 'Low concern'
    sources_used: int
    response_time_ms: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Latency / Benchmark
# ─────────────────────────────────────────────────────────────────────────────

class LatencyStats(BaseModel):
    tag: str
    n_requests: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


class LatencyStatsResponse(BaseModel):
    stats: list[LatencyStats]
    improvement_pct: Optional[float] = Field(
        None,
        description="% latency reduction: optimized vs naive. Null if only one tag present."
    )
    optimized_p95_ms: Optional[float]


# ─────────────────────────────────────────────────────────────────────────────
# News and Sentiment
# ─────────────────────────────────────────────────────────────────────────────

class NewsItem(BaseModel):
    headline: str
    publisher: str
    link: str
    time: str
    sentiment: str
    score: float
    effect: str
    summary: Optional[str] = ""


class StressedCompanyInfo(BaseModel):
    ticker: str
    base_score: float
    stressed_score: float
    net_sentiment: int
    status: str


class SentimentPortfolioResponse(BaseModel):
    base_var_95: float
    base_cvar_95: float
    sentiment_var_95: float
    sentiment_cvar_95: float
    net_portfolio_sentiment: int
    stressed_companies: list[StressedCompanyInfo]
