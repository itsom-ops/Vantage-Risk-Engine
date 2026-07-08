# Vantage Risk — AI Credit Risk Intelligence Platform

> **Built for UBS interview demonstration | July 2026**

An end-to-end credit risk intelligence platform that ingests real financial data,
scores companies with deterministic models (Altman Z + Merton DTD), explains
risk drivers with SHAP attribution, generates analyst narratives via Claude RAG,
and measures every claim with a real latency benchmark.

---

## Architecture

```
React + Vite + Tailwind + Framer Motion  (Vercel)
           │
           ▼
FastAPI backend  (Railway)
  ├── risk_engine.py     → Altman Z-Score, Merton DTD, SHAP explainability
  ├── rag_engine.py      → all-MiniLM-L6-v2 embeddings + pgvector retrieval + Claude narrative
  ├── routes/            → /companies, /portfolio/risk, /scenario, /insight, /latency-stats
  └── middleware/latency → logs every request to query_logs table
           │
           ▼
Supabase (PostgreSQL + pgvector)
  companies | financials | risk_scores | filing_chunks | query_logs
```

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 20+
- A free Supabase project (enable pgvector extension)
- Anthropic API key

### 2. Data Pipeline

```bash
cd vantage-risk-pipeline
pip install -r requirements.txt
cp .env.example .env      # fill in DATABASE_URL + ANTHROPIC_API_KEY

# Run schema in Supabase SQL editor first
python ingest.py          # fetch 30 companies from yfinance
```

### 3. Backend API

```bash
cd vantage-risk-api
pip install -r requirements.txt
cp .env.example .env      # same DATABASE_URL + ANTHROPIC_API_KEY

# Ingest SEC 10-K filings for RAG corpus
python scripts/ingest_filings.py

# Start API
uvicorn main:app --reload --port 8000
```

### 4. Frontend

```bash
cd vantage-risk-ui
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev               # → http://localhost:5173
```

### 5. Run Benchmark

```bash
cd vantage-risk-api
python benchmark.py --url http://localhost:8000 --n 100
# Output: benchmark_results.json with p50/p95/p99 per tag
```

---

## Data Flow

1. `ingest.py` → pulls fundamentals from yfinance for 30 tickers
2. `risk_engine.py` → Altman Z + Merton DTD + SHAP computed after ingestion
3. `scripts/ingest_filings.py` → pulls 10-K Risk Factor text from SEC EDGAR
4. `rag_engine.py` → embeds chunks with `all-MiniLM-L6-v2`, stores in pgvector
5. `/insight` endpoint → retrieves top-5 chunks + risk metrics → Claude narrative
6. `benchmark.py` → 100 requests × 2 tags → stores latency in `query_logs`
7. `/latency-stats` → returns p50/p95/p99 improvement %

---

## Benchmark Results

> Run `benchmark.py` to generate your own numbers. Example output:

```
── NAIVE ──────────────────────────────────
   n=100 | avg=1847ms | p50=1820ms | p95=2310ms | p99=2650ms

── OPTIMIZED ──────────────────────────────
   n=100 | avg=52ms | p50=38ms | p95=124ms | p99=195ms

  Naive p95:     2310ms
  Optimized p95: 124ms
  Improvement:   94.6%  ✅
```

---

## Models

### Altman Z-Score (1968)
```
Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
X1 = Working Capital / Total Assets
X2 = Retained Earnings / Total Assets
X3 = EBIT / Total Assets
X4 = Market Value Equity / Book Value Total Liabilities
X5 = Revenue / Total Assets

Thresholds: Z > 2.99 → Safe | 1.81–2.99 → Grey Zone | < 1.81 → Distress
```

### Merton Distance-to-Default
```
DD = [ln(V/D) + (r - ½σ²)T] / (σ√T)
PD = N(-DD)
```

### SHAP Attribution
Manual gradient method: SHAP_i = weight_i × (actual_i - baseline_i)
Top 3 drivers by |SHAP| shown in the UI with plain-language sentences.

---

## Deploy

- **Backend**: Connect `vantage-risk-api/` to Railway → set env vars → auto-deploys
- **Frontend**: Connect `vantage-risk-ui/` to Vercel → set `VITE_API_URL` → auto-deploys
- **Database**: Supabase (already hosted) — run `schema.sql` once

---

*Built with: FastAPI · Supabase · pgvector · sentence-transformers · Anthropic Claude · React · Vite · Tailwind · Framer Motion · Recharts*
