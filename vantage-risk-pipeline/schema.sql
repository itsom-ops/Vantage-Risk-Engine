-- schema.sql
-- Run this against your Supabase project ONCE.
-- Steps:
--   1. Open Supabase Dashboard → SQL Editor
--   2. Paste the full file and click Run
--   3. Then enable pgvector: Database → Extensions → search "vector" → Enable

-- ─────────────────────────────────────────────────────────────────────────────
-- Extensions
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────────────────────
-- companies
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker          TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    sector          TEXT,
    industry        TEXT,
    country         TEXT DEFAULT 'US',
    exchange        TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies (ticker);
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies (sector);

-- ─────────────────────────────────────────────────────────────────────────────
-- financials
-- One row per company per reporting period (annual).
-- All monetary values in USD millions.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS financials (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id              UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period                  TEXT NOT NULL,           -- e.g. "2023-12-31"
    fiscal_year             INTEGER,
    -- Income Statement
    revenue                 NUMERIC(20,4),
    ebit                    NUMERIC(20,4),
    net_income              NUMERIC(20,4),
    interest_expense        NUMERIC(20,4),
    -- Balance Sheet
    total_assets            NUMERIC(20,4),
    total_liabilities       NUMERIC(20,4),
    total_equity            NUMERIC(20,4),
    current_assets          NUMERIC(20,4),
    current_liabilities     NUMERIC(20,4),
    retained_earnings       NUMERIC(20,4),
    long_term_debt          NUMERIC(20,4),
    cash_and_equivalents    NUMERIC(20,4),
    -- Market Data
    market_cap              NUMERIC(20,4),
    shares_outstanding      NUMERIC(20,4),
    stock_price             NUMERIC(20,4),
    beta                    NUMERIC(10,6),
    -- Derived / pre-computed
    working_capital         NUMERIC(20,4) GENERATED ALWAYS AS (current_assets - current_liabilities) STORED,
    debt_to_equity          NUMERIC(10,6),
    current_ratio           NUMERIC(10,6),
    interest_coverage       NUMERIC(10,6),
    price_volatility_annual NUMERIC(10,6),   -- annualised σ from daily returns
    ingested_at             TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, period)
);

CREATE INDEX IF NOT EXISTS idx_financials_company ON financials (company_id);
CREATE INDEX IF NOT EXISTS idx_financials_period  ON financials (period);

-- ─────────────────────────────────────────────────────────────────────────────
-- risk_scores
-- Computed after ingestion.  One row per company per period.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_scores (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id           UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period               TEXT NOT NULL,
    -- Altman Z-Score
    altman_z             NUMERIC(10,4),
    altman_tier          TEXT CHECK (altman_tier IN ('Safe', 'Grey Zone', 'Distress')),
    -- Altman factors (stored for SHAP / explainability)
    x1_working_cap_ratio NUMERIC(10,6),
    x2_retained_earn_ratio NUMERIC(10,6),
    x3_ebit_ratio        NUMERIC(10,6),
    x4_equity_debt_ratio NUMERIC(10,6),
    x5_sales_ratio       NUMERIC(10,6),
    -- Merton Distance-to-Default
    distance_to_default  NUMERIC(10,6),
    prob_of_default      NUMERIC(10,8),    -- 0-1
    -- Composite score (0-100, higher = riskier)
    composite_risk_score NUMERIC(6,2),
    risk_tier            TEXT CHECK (risk_tier IN ('Low', 'Medium', 'High', 'Critical')),
    -- Explainability
    top_risk_driver_1    TEXT,
    top_risk_driver_2    TEXT,
    top_risk_driver_3    TEXT,
    -- Metadata
    computed_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, period)
);

CREATE INDEX IF NOT EXISTS idx_risk_company ON risk_scores (company_id);
CREATE INDEX IF NOT EXISTS idx_risk_tier    ON risk_scores (risk_tier);

-- ─────────────────────────────────────────────────────────────────────────────
-- filing_chunks
-- 500-token chunks from SEC 10-K risk factor sections.
-- Embedding = all-MiniLM-L6-v2 (dim=384)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS filing_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    filing_date     TEXT,
    form_type       TEXT DEFAULT '10-K',
    section         TEXT DEFAULT 'Risk Factors',
    chunk_index     INTEGER,
    chunk_text      TEXT NOT NULL,
    token_count     INTEGER,
    embedding       vector(384),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast approximate nearest-neighbour search
CREATE INDEX IF NOT EXISTS idx_filing_chunks_embedding
    ON filing_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_filing_chunks_company ON filing_chunks (company_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- query_logs
-- Every API request is logged here. Powers /latency-stats and the
-- benchmark comparison between 'naive' and 'optimized' code paths.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS query_logs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint         TEXT NOT NULL,
    company_id       UUID REFERENCES companies(id),
    query_text       TEXT,
    response_time_ms NUMERIC(10,3) NOT NULL,
    cache_hit        BOOLEAN DEFAULT FALSE,
    tag              TEXT DEFAULT 'live',   -- 'live' | 'naive' | 'optimized'
    status_code      INTEGER,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_logs_tag       ON query_logs (tag);
CREATE INDEX IF NOT EXISTS idx_query_logs_endpoint  ON query_logs (endpoint);
CREATE INDEX IF NOT EXISTS idx_query_logs_created   ON query_logs (created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Helper view: latest risk score per company
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW latest_risk_scores AS
SELECT DISTINCT ON (rs.company_id)
    c.id,
    c.ticker,
    c.name,
    c.sector,
    rs.period,
    rs.altman_z,
    rs.altman_tier,
    rs.distance_to_default,
    rs.prob_of_default,
    rs.composite_risk_score,
    rs.risk_tier,
    rs.top_risk_driver_1,
    rs.top_risk_driver_2,
    rs.top_risk_driver_3,
    rs.computed_at
FROM risk_scores rs
JOIN companies c ON c.id = rs.company_id
ORDER BY rs.company_id, rs.period DESC;
