"""
mock_server.py — Zero-dependency demo server for Vantage Risk UI.

Returns realistic pre-seeded data for all endpoints so the frontend
works fully without a Supabase connection or Anthropic key.

Run with:  python mock_server.py
"""

import random
import time
import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Vantage Risk — Demo Mode", version="1.0.0-demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Seeded company data ───────────────────────────────────────────────────────
COMPANIES = [
    {"id": "aapl-uuid-0001", "ticker": "AAPL", "name": "Apple Inc.",           "sector": "Technology",        "altman_z": 6.21, "altman_tier": "Safe",      "composite_risk_score": 12.4,  "risk_tier": "Low",      "prob_of_default": 0.0031},
    {"id": "msft-uuid-0002", "ticker": "MSFT", "name": "Microsoft Corp.",       "sector": "Technology",        "altman_z": 5.87, "altman_tier": "Safe",      "composite_risk_score": 15.2,  "risk_tier": "Low",      "prob_of_default": 0.0041},
    {"id": "jpm--uuid-0003", "ticker": "JPM",  "name": "JPMorgan Chase",        "sector": "Financial Services","altman_z": 3.44, "altman_tier": "Safe",      "composite_risk_score": 28.1,  "risk_tier": "Low",      "prob_of_default": 0.0089},
    {"id": "nee--uuid-0004", "ticker": "NEE",  "name": "NextEra Energy",        "sector": "Utilities",         "altman_z": 2.81, "altman_tier": "Safe",      "composite_risk_score": 33.7,  "risk_tier": "Medium",   "prob_of_default": 0.0182},
    {"id": "xom--uuid-0005", "ticker": "XOM",  "name": "ExxonMobil Corp.",      "sector": "Energy",            "altman_z": 2.65, "altman_tier": "Grey Zone", "composite_risk_score": 39.2,  "risk_tier": "Medium",   "prob_of_default": 0.0241},
    {"id": "f----uuid-0006", "ticker": "F",    "name": "Ford Motor Co.",         "sector": "Auto",              "altman_z": 2.10, "altman_tier": "Grey Zone", "composite_risk_score": 52.8,  "risk_tier": "Medium",   "prob_of_default": 0.0489},
    {"id": "gm---uuid-0007", "ticker": "GM",   "name": "General Motors",        "sector": "Auto",              "altman_z": 1.97, "altman_tier": "Grey Zone", "composite_risk_score": 57.4,  "risk_tier": "Medium",   "prob_of_default": 0.0612},
    {"id": "dal--uuid-0008", "ticker": "DAL",  "name": "Delta Air Lines",       "sector": "Airlines",          "altman_z": 1.74, "altman_tier": "Distress",  "composite_risk_score": 63.1,  "risk_tier": "High",     "prob_of_default": 0.0843},
    {"id": "ba---uuid-0009", "ticker": "BA",   "name": "Boeing Co.",            "sector": "Aerospace",         "altman_z": 1.42, "altman_tier": "Distress",  "composite_risk_score": 71.8,  "risk_tier": "High",     "prob_of_default": 0.1124},
    {"id": "t----uuid-0010", "ticker": "T",    "name": "AT&T Inc.",             "sector": "Telecom",           "altman_z": 1.38, "altman_tier": "Distress",  "composite_risk_score": 74.3,  "risk_tier": "High",     "prob_of_default": 0.1287},
    {"id": "ccl--uuid-0011", "ticker": "CCL",  "name": "Carnival Corp.",        "sector": "Leisure",           "altman_z": 1.21, "altman_tier": "Distress",  "composite_risk_score": 79.6,  "risk_tier": "High",     "prob_of_default": 0.1644},
    {"id": "wba--uuid-0012", "ticker": "WBA",  "name": "Walgreens Boots",       "sector": "Retail",            "altman_z": 1.05, "altman_tier": "Distress",  "composite_risk_score": 83.2,  "risk_tier": "Critical", "prob_of_default": 0.2103},
    {"id": "para-uuid-0013", "ticker": "PARA", "name": "Paramount Global",      "sector": "Media",             "altman_z": 0.94, "altman_tier": "Distress",  "composite_risk_score": 86.7,  "risk_tier": "Critical", "prob_of_default": 0.2541},
    {"id": "amc--uuid-0014", "ticker": "AMC",  "name": "AMC Entertainment",     "sector": "Entertainment",     "altman_z": 0.31, "altman_tier": "Distress",  "composite_risk_score": 94.8,  "risk_tier": "Critical", "prob_of_default": 0.4812},
    {"id": "pg---uuid-0015", "ticker": "PG",   "name": "Procter & Gamble",      "sector": "Consumer Staples",  "altman_z": 4.92, "altman_tier": "Safe",      "composite_risk_score": 18.6,  "risk_tier": "Low",      "prob_of_default": 0.0058},
    {"id": "v----uuid-0016", "ticker": "V",    "name": "Visa Inc.",             "sector": "Financial Services","altman_z": 5.14, "altman_tier": "Safe",      "composite_risk_score": 16.9,  "risk_tier": "Low",      "prob_of_default": 0.0047},
    {"id": "unh--uuid-0017", "ticker": "UNH",  "name": "UnitedHealth Group",    "sector": "Healthcare",        "altman_z": 4.33, "altman_tier": "Safe",      "composite_risk_score": 21.4,  "risk_tier": "Low",      "prob_of_default": 0.0072},
    {"id": "hd---uuid-0018", "ticker": "HD",   "name": "Home Depot Inc.",       "sector": "Retail",            "altman_z": 3.87, "altman_tier": "Safe",      "composite_risk_score": 24.8,  "risk_tier": "Low",      "prob_of_default": 0.0098},
    {"id": "vfc--uuid-0019", "ticker": "VFC",  "name": "VF Corporation",        "sector": "Apparel",           "altman_z": 1.61, "altman_tier": "Distress",  "composite_risk_score": 67.3,  "risk_tier": "High",     "prob_of_default": 0.0967},
    {"id": "tlry-uuid-0020", "ticker": "TLRY", "name": "Tilray Brands",         "sector": "Cannabis",          "altman_z": 0.54, "altman_tier": "Distress",  "composite_risk_score": 91.2,  "risk_tier": "Critical", "prob_of_default": 0.3841},
]

SHAP_DRIVERS = {
    "AAPL": [
        "Strong EBIT margin (X3=0.324) is the primary driver of low credit risk, providing robust debt-servicing capacity.",
        "High market equity-to-debt ratio (X4=10.31) reflects substantial balance-sheet cushion against default.",
        "Strong asset turnover (X5=1.087) indicates efficient capital deployment and cash generation.",
    ],
    "BA": [
        "Negative EBIT ratio (X3=-0.016) indicates the firm is not generating operating profit — a primary distress signal.",
        "Negative retained earnings ratio (X2=-0.136) from accumulated losses erodes the internal capital base significantly.",
        "High leverage ratio is a primary driver of elevated credit risk given total liabilities exceed equity.",
    ],
    "AMC": [
        "Negative EBIT indicates the firm is not generating operating profit — distress signal.",
        "Accumulated losses erode the retained earnings cushion — elevated reinvestment risk.",
        "Negative working capital signals potential near-term liquidity pressure.",
    ],
    "DAL": [
        "High leverage ratio is the primary driver of elevated credit risk.",
        "Low working capital ratio indicates limited short-term financial buffer.",
        "Thin operating margins reduce the firm's debt-servicing headroom.",
    ],
}
DEFAULT_DRIVERS = [
    "High leverage ratio is the primary driver of elevated credit risk.",
    "Thin operating margins reduce the firm's debt-servicing headroom.",
    "Low asset utilisation reduces the firm's ability to generate cash for debt service.",
]

_latency_history = []

# ── Helper ───────────────────────────────────────────────────────────────────
def fetch_company_live_mock(ticker: str):
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or "totalAssets" not in info:
            return None
            
        ta = info.get("totalAssets", 1000) or 1000
        tl = info.get("totalDebt", info.get("totalLiab", 500)) or 500
        mve = info.get("marketCap", 1000) or 1000
        eb = info.get("ebit", 100) or 100
        wc = (info.get("totalCurrentAssets", 500) or 500) - (info.get("totalCurrentLiabilities", 400) or 400)
        re = info.get("retainedEarnings", 50) or 50
        rev = info.get("totalRevenue", 500) or 500
        
        x1 = wc / ta
        x2 = re / ta
        x3 = eb / ta
        x4 = mve / tl if tl > 0 else 1.0
        x5 = rev / ta
        
        z = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
        
        if z > 2.99: tier = "Safe"
        elif z > 1.81: tier = "Grey Zone"
        else: tier = "Distress"
        
        comp_score = max(0.0, min(100.0, round((2.99 - z) / (2.99 - (-2.0)) * 100, 2)))
        
        if comp_score < 25: risk_tier = "Low"
        elif comp_score < 50: risk_tier = "Medium"
        elif comp_score < 75: risk_tier = "High"
        else: risk_tier = "Critical"
        
        pd = 1.0 - math.exp(-comp_score / 200.0)
        
        comp_data = {
            "id": f"{ticker.lower()}-uuid-live",
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker.upper()),
            "sector": info.get("sector", "Unknown"),
            "altman_z": round(z, 2),
            "altman_tier": tier,
            "composite_risk_score": comp_score,
            "risk_tier": risk_tier,
            "prob_of_default": round(pd, 4),
        }
        
        drivers = [
            f"Altman Z-Score of {z:.2f} driven by asset size and capital structure.",
            f"Market cap cushion X4={x4:.2f} relative to liabilities.",
            f"Operating efficiency ratio X3={x3:.2f} compared to historical industry standard."
        ]
        SHAP_DRIVERS[ticker.upper()] = drivers
        
        COMPANIES.append(comp_data)
        return comp_data
    except Exception as exc:
        print(f"Error fetching mock live ticker {ticker}: {exc}")
        return None

def get_company(company_id: str):
    for c in COMPANIES:
        if c["id"] == company_id or c["ticker"] == company_id or c["ticker"].lower() == company_id.lower():
            return c
    if len(company_id) <= 6:
        return fetch_company_live_mock(company_id)
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "db_connected": True, "version": "1.0.0-demo", "mode": "mock"}


@app.get("/companies")
def list_companies():
    return [
        {**c, "country": "US", "period": "2024-12-31"}
        for c in COMPANIES
    ]


@app.get("/companies/{company_id}/risk")
def get_company_risk(company_id: str):
    t0 = time.perf_counter()
    c = get_company(company_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")

    drivers = SHAP_DRIVERS.get(c["ticker"], DEFAULT_DRIVERS)
    elapsed = round((time.perf_counter() - t0) * 1000 + random.uniform(8, 45), 2)
    _latency_history.append(elapsed)

    z = c["altman_z"]
    return {
        **c,
        "country": "US",
        "period": "2024-12-31",
        "computed_at": "2024-12-31T00:00:00Z",
        "x1_working_cap_ratio":   round(0.05 + (z - 0.3) * 0.03, 4),
        "x2_retained_earn_ratio": round(-0.1 + (z - 0.3) * 0.04, 4),
        "x3_ebit_ratio":          round(-0.02 + (z - 0.3) * 0.05, 4),
        "x4_equity_debt_ratio":   round(0.2 + (z - 0.3) * 0.8, 4),
        "x5_sales_ratio":         round(0.3 + (z - 0.3) * 0.12, 4),
        "distance_to_default":    round(max(0.1, z - 0.5 + random.uniform(-0.1, 0.1)), 4),
        "shap_drivers": [
            {"feature": f"driver_{i+1}", "raw_value": 0.0, "shap_value": round(0.8 - i*0.2, 4),
             "direction": "low", "plain_text": d}
            for i, d in enumerate(drivers)
        ],
        "top_risk_driver_1": drivers[0],
        "top_risk_driver_2": drivers[1],
        "top_risk_driver_3": drivers[2],
        "response_time_ms": elapsed,
    }


@app.get("/companies/{company_id}/news")
def get_company_news(company_id: str):
    c = get_company(company_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Company not found")
        
    ticker = c["ticker"]
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
        yf_news = t.news or []
    except Exception:
        yf_news = []
        
    if not yf_news:
        yf_news = [
            {"title": f"Analysts update credit outlook for {ticker} following quarterly report", "publisher": "Reuters", "link": "#"},
            {"title": f"Market volatility shifts option trading patterns in {ticker} shares", "publisher": "Bloomberg", "link": "#"},
            {"title": f"Industry sector rotation creates headwinds for {ticker} and competitors", "publisher": "Financial Times", "link": "#"},
        ]
        
    processed = []
    bearish_keywords = ["delay", "fail", "drop", "fine", "probe", "cut", "risk", "debt", "lower", "lawsuit", "crash", "decline", "warn", "underperform", "antitrust"]
    bullish_keywords = ["beat", "surge", "gain", "buy", "upgrade", "rise", "grow", "strong", "higher", "profit", "win", "partnership", "success"]
    
    for item in yf_news[:5]:
        title = item.get("title", "")
        sent = "Neutral"
        score_val = 0.0
        effect = "No immediate impact on Altman Z-Score ratios expected."
        
        t_lower = title.lower()
        if any(w in t_lower for w in bearish_keywords):
            sent = "Bearish"
            score_val = -round(random.uniform(0.1, 0.4), 2)
            if "debt" in t_lower or "liabilit" in t_lower or "leverage" in t_lower:
                effect = "Increased debt service burden will degrade Altman X4 (Equity/Debt) ratio."
            elif "profit" in t_lower or "ebit" in t_lower or "revenue" in t_lower or "sale" in t_lower:
                effect = "Lower operating profitability will compress Altman X3 (EBIT/Assets) ratio."
            else:
                effect = "Negative operational headwinds could reduce Altman X3 (EBIT) ratio."
        elif any(w in t_lower for w in bullish_keywords):
            sent = "Bullish"
            score_val = round(random.uniform(0.1, 0.4), 2)
            if "profit" in t_lower or "ebit" in t_lower or "revenue" in t_lower or "sale" in t_lower:
                effect = "Stronger revenues will improve Altman X5 (Sales/Assets) and operating margin X3."
            else:
                effect = "Positive market dynamics support overall asset utilization ratios."
                
        processed.append({
            "headline": title,
            "publisher": item.get("publisher", "Financial News"),
            "link": item.get("link", "#"),
            "time": "Recent",
            "sentiment": sent,
            "score": score_val,
            "effect": effect
        })
        
    return processed


@app.get("/companies/{company_id}/news-correlation")
def get_company_news_correlation(company_id: str):
    c = get_company(company_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Company not found")
    ticker = c["ticker"]
    return {
        "correlation_summary": f"No clear correlation observed. Analysis of {ticker} over the past 5 days indicates a flat stock price trend (+0.45% change), while the recent news feed shows a neutral to slightly bullish sentiment. Therefore, news sentiment has not acted as a primary driver of trading fluctuations in the current window."
    }


@app.get("/companies/{company_id}/risk-matrix")
def get_company_risk_matrix(company_id: str):
    c = get_company(company_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Company not found")
    
    ticker = c["ticker"]
    altman_z = float(c.get("altman_z", 2.5))
    altman_tier = c.get("altman_tier", "Grey Zone")
    
    z_sev = "High" if altman_z < 1.8 else ("Medium" if altman_z < 3.0 else "Low")

    return {
        "credit_risks": [
            {"title": "Default Exposure & Asset Structure", "value": f"{altman_z:.2f}", "severity": z_sev, "explanation": f"Altman Z-Score of {altman_z:.2f} places company in the {altman_tier} tier."},
            {"title": "Transaction Risk (Stock Volume Proxy)", "value": "0.45%", "severity": "Low", "explanation": "Average daily trading value accounts for 0.45% of market capitalization."},
            {"title": "Portfolio Concentration Proxy", "value": "N/A", "severity": "Low", "explanation": "insufficient public data — proxy shown: business concentration risk is low."},
            {"title": "Product Development", "value": "7.2%", "severity": "Low", "explanation": "Research & development expense represents 7.2% of total annual revenues."},
            {"title": "Interest Rate Sensitivity", "value": "-1.2x", "severity": "Low", "explanation": "Stressed interest coverage ratio drops by 1.2x under scenario shock."}
        ],
        "liquidity_risks": [
            {"title": "Working Capital Buffer", "value": "$4,235.0M", "severity": "Low", "explanation": "Net working capital buffer stands at $4,235.0M USD assets over liabilities."},
            {"title": "Short-Term Liabilities", "value": "35.2%", "severity": "Low", "explanation": "Current liabilities represent 35.2% of total outstanding liabilities."},
            {"title": "Profitability Limits", "value": "18.5%", "severity": "Low", "explanation": "EBIT margin is calculated at 18.5% of annual revenues."},
            {"title": "Liquidity Ratios", "value": "1.45x", "severity": "Medium", "explanation": "Current ratio of 1.45x indicates short-term asset liquidity coverage."},
            {"title": "Funding Cost", "value": "3.80%", "severity": "Low", "explanation": "Estimated funding cost is 3.80% calculated from interest and liabilities."}
        ],
        "governance_risks": [
            {"title": "Retained Reserves & Capital Allocation", "value": "24.5%", "severity": "Low", "explanation": "Retained earnings constitute 24.5% of total asset base."},
            {"title": "Ownership Concentration", "value": "72.4%", "severity": "Low", "explanation": "Insider (2.1%) and institutional (70.3%) hold 72.4% of stock."},
            {"title": "Management Confidence Proxy", "value": "Positive Trend", "severity": "Low", "explanation": "Latest recommendation trend is Positive Trend over last 2 quarters."},
            {"title": "Oversight Effectiveness", "value": "SEC Excerpt", "severity": "Low", "explanation": "Filing governance check: no covenant terms observed"}
        ],
        "market_risks": [
            {"title": "EBIT Margin vs Asset Yield", "value": "6.2%", "severity": "Low", "explanation": "Asset yield (EBIT/Assets) is 6.2% relative to sector averages."},
            {"title": "Interest Rate Fluctuation", "value": "Cross-linked", "severity": "Low", "explanation": "Correlated to base rate scenario shocks and interest delta sensitivities."},
            {"title": "FX Exposure", "value": "Unavailable", "severity": "Low", "explanation": "insufficient public data — proxy shown: domestic revenue base predominates."},
            {"title": "Historical Volatility", "value": "24.5%", "severity": "Medium", "explanation": "Annualised historical price volatility is 24.5% over the past 12 months."}
        ],
        "external_risks": [
            {"title": "Macro / Sector Headwinds", "value": "1.12x", "severity": "Medium", "explanation": "Stock beta vs sector ETF is 1.12x over the past year."},
            {"title": "Competitor Dynamics", "value": "2.85", "severity": "Low", "explanation": f"Company Z-Score ({altman_z:.2f}) vs same-sector average of (2.85)."},
            {"title": "Macroeconomic Trends", "value": "Computed", "severity": "Low", "explanation": "Correlation of daily returns with 10-Yr Treasury Yield (^TNX) over 1 year is 0.12."},
            {"title": "Political / Regulatory Headwinds", "value": "News Scraped", "severity": "Low", "explanation": "no regulatory-flagged news in current window"}
        ],
        "legal_compliance": [
            {"title": "Filing Disclosure Transparency", "value": "Clean", "severity": "Low", "explanation": "SEC 10-K covenant search reference: no covenant terms observed"},
            {"title": "Antitrust / Regulatory Sanctions", "value": "News Flagged", "severity": "Low", "explanation": "no regulatory-flagged news in current window"}
        ]
    }


class SentimentPortfolioReq(BaseModel):
    company_ids: list[str]
    severity_multiplier: float = 1.0

@app.post("/portfolio/sentiment-adjusted-risk")
def sentiment_adjusted_portfolio_risk(req: SentimentPortfolioReq):
    import numpy as np
    scores = []
    stressed_scores = []
    vols = []
    stressed_vols = []
    
    net_sentiment_sum = 0
    stressed_list = []
    
    for cid in req.company_ids:
        c = get_company(cid)
        if not c:
            continue
            
        base_score = float(c["composite_risk_score"])
        ticker = c["ticker"]
        
        # Calculate net news sentiment
        news = get_company_news(cid)
        bearish_cnt = sum(1 for n in news if n["sentiment"] == "Bearish")
        bullish_cnt = sum(1 for n in news if n["sentiment"] == "Bullish")
        net_sent = bullish_cnt - bearish_cnt
        net_sentiment_sum += net_sent
        
        # Apply sentiment stress penalty
        stress_penalty = 0.0
        vol_stress = 1.0
        if net_sent < 0:
            # Negative sentiment increases risk score
            stress_penalty = abs(net_sent) * 8.0 * req.severity_multiplier
            stress_penalty = min(stress_penalty, 40.0) # cap
            vol_stress = 1.0 + abs(net_sent) * 0.15 * req.severity_multiplier
            
        stressed_score = min(100.0, base_score + stress_penalty)
        base_vol = 0.30
        
        scores.append(base_score)
        stressed_scores.append(stressed_score)
        vols.append(base_vol)
        stressed_vols.append(base_vol * vol_stress)
        
        stressed_list.append({
            "ticker": ticker,
            "base_score": round(base_score, 1),
            "stressed_score": round(stressed_score, 1),
            "net_sentiment": net_sent,
            "status": "Stressed" if stress_penalty > 0 else "Stable"
        })
        
    if not scores:
        scores, stressed_scores = [50.0], [50.0]
        vols, stressed_vols = [0.30], [0.30]
        
    # Simulation VaR/CVaR
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
    
    return {
        "base_var_95": round(base_var, 2),
        "base_cvar_95": round(base_cvar, 2),
        "sentiment_var_95": round(stressed_var, 2),
        "sentiment_cvar_95": round(stressed_cvar, 2),
        "net_portfolio_sentiment": net_sentiment_sum,
        "stressed_companies": stressed_list
    }


class PortfolioReq(BaseModel):
    company_ids: list[str]

@app.post("/portfolio/risk")
def portfolio_risk(req: PortfolioReq):
    scores = []
    tiers = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    worst_ticker, worst_score = None, -1.0
    for cid in req.company_ids:
        c = get_company(cid)
        if c:
            s = c["composite_risk_score"]
            scores.append(s)
            tiers[c["risk_tier"]] = tiers.get(c["risk_tier"], 0) + 1
            if s > worst_score:
                worst_score, worst_ticker = s, c["ticker"]
    if not scores:
        scores = [50.0]
    avg = sum(scores) / len(scores)
    return {
        "n_companies": len(scores),
        "var_95": round(avg * 1.18, 2),
        "cvar_95": round(avg * 1.34, 2),
        "avg_composite_score": round(avg, 2),
        "worst_company_ticker": worst_ticker,
        "worst_company_score": round(worst_score, 2),
        "risk_distribution": tiers,
    }


class ScenarioReq(BaseModel):
    company_id: str
    rate_shock_bps: int

@app.post("/scenario")
def scenario(req: ScenarioReq):
    c = get_company(req.company_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    base_z = c["altman_z"]
    # Each 100bps rate increase reduces Z by ~0.18 (simplified)
    delta_z = -(req.rate_shock_bps / 100) * 0.18
    stressed_z = round(max(0.0, base_z + delta_z), 2)

    def tier(z):
        if z > 2.99: return "Safe"
        if z > 1.81: return "Grey Zone"
        return "Distress"

    base_tier     = tier(base_z)
    stressed_tier = tier(stressed_z)
    extra_interest_m = abs(req.rate_shock_bps) * 0.8  # rough $M figure for narrative
    direction = "increase" if req.rate_shock_bps > 0 else "decrease"
    narrative = (
        f"A {abs(req.rate_shock_bps)}bps rate {direction} adds approximately "
        f"${extra_interest_m:.0f}M in estimated annual interest expense for {c['ticker']}. "
        f"Altman Z-Score shifts from {base_z:.2f} to {stressed_z:.2f} ({delta_z:+.2f})"
    )
    if base_tier != stressed_tier:
        narrative += f", moving the risk classification from '{base_tier}' to '{stressed_tier}'."
    else:
        narrative += f", remaining in the '{stressed_tier}' tier."

    return {
        "company_id": c["id"],
        "ticker": c["ticker"],
        "rate_shock_bps": req.rate_shock_bps,
        "base_altman_z": base_z,
        "stressed_altman_z": stressed_z,
        "base_tier": base_tier,
        "stressed_tier": stressed_tier,
        "base_interest_coverage": 4.2,
        "stressed_interest_coverage": round(4.2 - req.rate_shock_bps * 0.004, 2),
        "tier_changed": base_tier != stressed_tier,
        "narrative": narrative,
    }


class InsightReq(BaseModel):
    company_id: str
    query: str

NARRATIVES = {
    "AAPL": ("Apple's balance sheet remains exceptionally strong with a Merton Distance-to-Default "
             "of {dd:.2f}, supported by its dominant free cash flow generation of over $90B annually. "
             "The primary risk vector is concentration in hardware revenue and potential margin "
             "compression from intensifying competition in the services segment.",
             "Low concern"),
    "BA":   ("Boeing's Altman Z-Score of {z:.2f} places it firmly in the Distress tier, driven primarily "
             "by negative retained earnings of -$18.6B and persistent operating losses. "
             "The 737 MAX certification delays and ongoing 787 production issues continue "
             "to consume cash reserves at an elevated rate.",
             "Flag for review"),
    "AMC":  ("AMC Entertainment presents a critical credit risk profile with a composite score of "
             "{score:.0f}/100. Negative working capital and accumulated losses of over $3B create "
             "severe near-term liquidity pressure. The structural decline in theatrical attendance "
             "post-pandemic constrains any near-term recovery pathway.",
             "Flag for review"),
    "DAL":  ("Delta Air Lines operates in a structurally leveraged sector with current ratio of 0.84. "
             "While revenue recovery from pandemic lows has been robust, the elevated fuel cost "
             "environment and high fixed-cost base maintain the Z-Score in the Distress zone. "
             "Monitor fuel hedging programme and covenant compliance closely.",
             "Monitor"),
}
DEFAULT_NARRATIVE = (
    "{ticker}'s risk profile reflects {tier} credit conditions with a composite score of "
    "{score:.0f}/100 and Altman Z of {z:.2f}. "
    "The primary risk driver identified through SHAP attribution is leverage exposure, "
    "with debt-servicing capacity remaining the key credit variable to monitor. "
    "Current filing disclosures do not indicate imminent covenant breaches.",
    "Monitor"
)

@app.post("/insight")
def insight(req: InsightReq):
    t0 = time.perf_counter()
    c = get_company(req.company_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    template, recommendation = NARRATIVES.get(c["ticker"], DEFAULT_NARRATIVE)
    narrative = template.format(
        ticker=c["ticker"],
        z=c["altman_z"],
        score=c["composite_risk_score"],
        tier=c["risk_tier"],
        dd=max(0.1, c["altman_z"] - 0.5),
    )
    elapsed = round((time.perf_counter() - t0) * 1000 + random.uniform(380, 650), 2)
    _latency_history.append(elapsed)

    return {
        "company_id": c["id"],
        "ticker": c["ticker"],
        "query": req.query,
        "narrative": narrative,
        "recommendation": recommendation,
        "sources_used": random.randint(3, 5),
        "response_time_ms": elapsed,
    }


@app.get("/latency-stats")
def latency_stats():
    import statistics
    live = _latency_history[-50:] if _latency_history else [45.2, 38.1, 52.7, 41.3, 39.8]
    naive = [t * random.uniform(8, 12) for t in live[:20]] or [1800, 2100, 1950]
    optimized = live[:20] or [45, 38, 52]

    def pct(data, p):
        if not data: return 0.0
        s = sorted(data)
        k = (len(s) - 1) * p / 100
        lo, hi = int(k), min(int(k)+1, len(s)-1)
        return round(s[lo] + (s[hi]-s[lo])*(k-lo), 2)

    naive_p95 = pct(naive, 95)
    opt_p95   = pct(optimized, 95)
    improvement = round((naive_p95 - opt_p95) / naive_p95 * 100, 1) if naive_p95 > 0 else None

    return {
        "stats": [
            {"tag": "live",      "n_requests": len(live),      "avg_ms": round(statistics.mean(live), 2),      "p50_ms": pct(live, 50),      "p95_ms": pct(live, 95),      "p99_ms": pct(live, 99)},
            {"tag": "naive",     "n_requests": len(naive),     "avg_ms": round(statistics.mean(naive), 2),     "p50_ms": pct(naive, 50),     "p95_ms": naive_p95,          "p99_ms": pct(naive, 99)},
            {"tag": "optimized", "n_requests": len(optimized), "avg_ms": round(statistics.mean(optimized), 2), "p50_ms": pct(optimized, 50), "p95_ms": opt_p95,            "p99_ms": pct(optimized, 99)},
        ],
        "improvement_pct": improvement,
        "optimized_p95_ms": opt_p95,
    }


if __name__ == "__main__":
    import uvicorn
    print("\n*** Vantage Risk Mock Server ***")
    print("   API docs: http://localhost:8000/docs")
    print("   Frontend: http://localhost:5173\n")
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=False)
