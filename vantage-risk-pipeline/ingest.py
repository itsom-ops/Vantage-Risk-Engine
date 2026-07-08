"""
ingest.py — pulls fundamentals for 30 companies via yfinance,
computes the raw fields needed for Altman Z and Merton DTD,
and inserts them into Supabase via SQLAlchemy.

Usage:
    python ingest.py              # full run
    python ingest.py --dry-run    # print data, don't insert
"""

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import text

from config import SessionLocal, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Ticker universe — 30 companies across sectors.
# Includes a few known-distressed / high-risk names for realistic variance.
# ─────────────────────────────────────────────────────────────────────────────
TICKERS = [
    # ── Investment grade / Safe ──────────────────────────────────────────────
    "AAPL",   # Apple — tech, cash-rich
    "MSFT",   # Microsoft — mega-cap
    "JPM",    # JPMorgan Chase — large-cap bank
    "BRK-B",  # Berkshire Hathaway — conglomerate
    "JNJ",    # Johnson & Johnson — healthcare
    "PG",     # Procter & Gamble — consumer staples
    "V",      # Visa — payments, asset-light
    "UNH",    # UnitedHealth — health insurance
    "HD",     # Home Depot — retail
    "NEE",    # NextEra Energy — utilities

    # ── Mid-tier / Grey Zone ─────────────────────────────────────────────────
    "F",      # Ford — auto, high debt
    "GM",     # General Motors — auto
    "DAL",    # Delta Air Lines — cyclical, leveraged
    "CCL",    # Carnival — cruise, post-COVID recovery
    "XOM",    # ExxonMobil — commodity exposure
    "BA",     # Boeing — high leverage, operational issues
    "T",      # AT&T — heavy debt load
    "VFC",    # VF Corp — consumer discretionary, declining
    "WBA",    # Walgreens — pharmacy, distressed turnaround
    "PARA",   # Paramount — media disruption

    # ── High Risk / Distress ─────────────────────────────────────────────────
    "AMC",    # AMC Entertainment — heavily distressed
    "BBBY",   # Bed Bath & Beyond (now BBBYQ) — bankruptcy watch
    "RIDE",   # Lordstown Motors — EV startup, cash burn
    "NKLA",   # Nikola — negative book value territory
    "TLRY",   # Tilray — cannabis, persistent losses
    "BGFV",   # Big 5 Sporting Goods — declining margins
    "SPCE",   # Virgin Galactic — pre-revenue, high burn
    "PRTY",   # Party City — retail distress
    "BBAI",   # BigBear.ai — small cap, high burn
    "SHPW",   # Shapeways — 3D printing, tiny cap
]


def safe_get(info: dict, *keys, default=None):
    """Try multiple field names, return first non-None hit."""
    for key in keys:
        val = info.get(key)
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            return val
    return default


def compute_price_volatility(ticker_obj: yf.Ticker, period: str = "1y") -> Optional[float]:
    """Annualised historical volatility from daily returns."""
    try:
        hist = ticker_obj.history(period=period)
        if hist.empty or len(hist) < 20:
            return None
        daily_returns = hist["Close"].pct_change().dropna()
        return float(daily_returns.std() * np.sqrt(252))
    except Exception:
        return None


def fetch_company(ticker: str) -> Optional[dict]:
    """
    Fetch one company's fundamentals from yfinance.
    Returns a dict ready for DB insertion, or None if critically incomplete.
    """
    log.info(f"  Fetching {ticker} …")
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        # ── Identity fields ──────────────────────────────────────────────────
        name     = safe_get(info, "longName", "shortName", default=ticker)
        sector   = safe_get(info, "sector", default="Unknown")
        industry = safe_get(info, "industry", default="Unknown")
        country  = safe_get(info, "country", default="US")
        exchange = safe_get(info, "exchange", default=None)

        # ── Income Statement ─────────────────────────────────────────────────
        revenue           = safe_get(info, "totalRevenue")
        ebit              = safe_get(info, "ebit")
        net_income        = safe_get(info, "netIncomeToCommon")
        interest_expense  = safe_get(info, "interestExpense")

        # ── Balance Sheet ────────────────────────────────────────────────────
        total_assets      = safe_get(info, "totalAssets")
        total_liabilities = safe_get(info, "totalDebt", "totalLiab")
        total_equity      = safe_get(info, "totalStockholderEquity", "bookValue")
        current_assets    = safe_get(info, "totalCurrentAssets")
        current_liabilities = safe_get(info, "totalCurrentLiabilities")
        retained_earnings = safe_get(info, "retainedEarnings")
        long_term_debt    = safe_get(info, "longTermDebt")
        cash              = safe_get(info, "totalCash", "cash")

        # ── Market Data ──────────────────────────────────────────────────────
        market_cap        = safe_get(info, "marketCap")
        shares_out        = safe_get(info, "sharesOutstanding")
        stock_price       = safe_get(info, "currentPrice", "regularMarketPrice")
        beta              = safe_get(info, "beta")

        # ── Derived ratios ───────────────────────────────────────────────────
        debt_to_equity = (
            round(total_liabilities / total_equity, 6)
            if total_equity and total_equity != 0 else None
        )
        current_ratio = (
            round(current_assets / current_liabilities, 6)
            if current_liabilities and current_liabilities != 0 else None
        )
        interest_coverage = (
            round(ebit / abs(interest_expense), 6)
            if ebit and interest_expense and interest_expense != 0 else None
        )

        # ── Volatility (from price history) ─────────────────────────────────
        vol = compute_price_volatility(t)

        # ── Critical completeness check ──────────────────────────────────────
        # We need at least total_assets and one income figure to be useful.
        if total_assets is None or total_assets == 0:
            log.warning(f"  ⚠  {ticker}: total_assets missing — skipping.")
            return None

        period_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "country": country,
            "exchange": exchange,
            # Financials
            "period": period_str,
            "fiscal_year": datetime.now().year,
            "revenue": revenue,
            "ebit": ebit,
            "net_income": net_income,
            "interest_expense": interest_expense,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "retained_earnings": retained_earnings,
            "long_term_debt": long_term_debt,
            "cash_and_equivalents": cash,
            "market_cap": market_cap,
            "shares_outstanding": shares_out,
            "stock_price": stock_price,
            "beta": beta,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "interest_coverage": interest_coverage,
            "price_volatility_annual": vol,
        }

    except Exception as exc:
        log.error(f"  ✗  {ticker}: unhandled error — {exc}")
        return None


def upsert_company(session, data: dict) -> str:
    """Insert or update companies + financials. Returns company UUID."""
    # ── Upsert company ───────────────────────────────────────────────────────
    result = session.execute(
        text("""
            INSERT INTO companies (ticker, name, sector, industry, country, exchange)
            VALUES (:ticker, :name, :sector, :industry, :country, :exchange)
            ON CONFLICT (ticker) DO UPDATE
                SET name=EXCLUDED.name, sector=EXCLUDED.sector,
                    industry=EXCLUDED.industry
            RETURNING id
        """),
        {
            "ticker":   data["ticker"],
            "name":     data["name"],
            "sector":   data["sector"],
            "industry": data["industry"],
            "country":  data["country"],
            "exchange": data["exchange"],
        },
    )
    company_id = str(result.fetchone()[0])

    # ── Upsert financials ────────────────────────────────────────────────────
    session.execute(
        text("""
            INSERT INTO financials (
                company_id, period, fiscal_year,
                revenue, ebit, net_income, interest_expense,
                total_assets, total_liabilities, total_equity,
                current_assets, current_liabilities, retained_earnings,
                long_term_debt, cash_and_equivalents,
                market_cap, shares_outstanding, stock_price, beta,
                debt_to_equity, current_ratio, interest_coverage,
                price_volatility_annual
            ) VALUES (
                :company_id, :period, :fiscal_year,
                :revenue, :ebit, :net_income, :interest_expense,
                :total_assets, :total_liabilities, :total_equity,
                :current_assets, :current_liabilities, :retained_earnings,
                :long_term_debt, :cash_and_equivalents,
                :market_cap, :shares_outstanding, :stock_price, :beta,
                :debt_to_equity, :current_ratio, :interest_coverage,
                :price_volatility_annual
            )
            ON CONFLICT (company_id, period) DO UPDATE
                SET revenue=EXCLUDED.revenue, ebit=EXCLUDED.ebit,
                    total_assets=EXCLUDED.total_assets,
                    market_cap=EXCLUDED.market_cap,
                    stock_price=EXCLUDED.stock_price,
                    price_volatility_annual=EXCLUDED.price_volatility_annual,
                    ingested_at=NOW()
        """),
        {"company_id": company_id, **data},
    )

    return company_id


def run_ingest(dry_run: bool = False) -> None:
    log.info("=" * 60)
    log.info("Vantage Risk — Data Ingestion")
    log.info(f"Tickers: {len(TICKERS)} | Dry-run: {dry_run}")
    log.info("=" * 60)

    results = {"ok": 0, "skipped": 0, "errors": 0}
    session = None if dry_run else SessionLocal()

    try:
        for ticker in TICKERS:
            data = fetch_company(ticker)
            if data is None:
                results["skipped"] += 1
                continue

            if dry_run:
                log.info(f"  [DRY-RUN] {ticker}: {data['name']} | "
                         f"assets={data['total_assets']} | sector={data['sector']}")
                results["ok"] += 1
                continue

            try:
                company_id = upsert_company(session, data)
                session.commit()
                log.info(f"  ✅  {ticker} ({data['name']}) → {company_id[:8]}…")
                results["ok"] += 1
            except Exception as exc:
                session.rollback()
                log.error(f"  ✗  {ticker}: DB error — {exc}")
                results["errors"] += 1

    finally:
        if session:
            session.close()

    log.info("")
    log.info("─" * 40)
    log.info(f"Done: {results['ok']} inserted | "
             f"{results['skipped']} skipped | "
             f"{results['errors']} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vantage Risk data ingestion")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print fetched data without writing to DB")
    args = parser.parse_args()
    run_ingest(dry_run=args.dry_run)
