# Vantage Risk — UBS Interview Prep Guide

> **90-second pitch, 20 deep-dive questions, all grounded in real code.**

---

## The 90-Second Verbal Walkthrough

> Practice this until it flows naturally.

**"Vantage Risk is an AI-powered credit risk intelligence platform I built end-to-end.
The problem it solves: credit analysts spend hours manually parsing 10-Ks to assess
a company's default probability. We compressed that to under 2 seconds.

The architecture: a FastAPI backend ingests real fundamentals from yfinance and SEC EDGAR,
computes Altman Z-Scores and Merton Distance-to-Default deterministically — no black box —
then layers Claude on top purely for narrative generation, grounded strictly in retrieved
filing text via pgvector RAG.

The differentiator: every risk score comes with SHAP attribution showing the top 3
financial drivers in plain language. That's the gap most AI finance tools miss.

On performance: I ran a proper 100-request benchmark — naive path vs optimised (LRU cache
+ pgvector index). p95 latency dropped from 2.3 seconds to 124ms — a 94% reduction —
and I have the JSON file to prove it."**

---

## 20 Deep-Dive Questions + Model Answers

---

### SECTION 1: Financial Models

---

**Q1: Walk me through the Altman Z-Score formula. Why this model specifically?**

Altman Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5

- X1 = Working Capital / Total Assets → liquidity
- X2 = Retained Earnings / Total Assets → historical profitability
- X3 = EBIT / Total Assets → operating efficiency
- X4 = Market Value Equity / Book Value Total Liabilities → leverage cushion
- X5 = Revenue / Total Assets → asset utilisation

Thresholds: Z > 2.99 = Safe | 1.81–2.99 = Grey Zone | < 1.81 = Distress.

I chose it because it's **interpretable, academically grounded (Altman 1968), and auditable**.
For a linear model, the SHAP decomposition is exact — the weights are the coefficients.
Code: `risk_engine.py:altman_z_score()`

---

**Q2: What's the Merton Distance-to-Default and why use it alongside Altman?**

DD = [ln(V/D) + (r - ½σ²)T] / (σ√T)  
PD = N(-DD)

V = asset value (market cap + liabilities), D = debt face value, σ = asset volatility.

Altman is backward-looking (accounting ratios). Merton is **forward-looking** — it
incorporates current market pricing and volatility. Enron looked fine on accounting
ratios while equity collapsed. Using both gives a richer picture.

Code: `risk_engine.py:merton_distance_to_default()`

---

**Q3: Your SHAP implementation — how is it different from running SHAP on a trained model?**

Standard SHAP requires a fitted model + Shapley decomposition over the feature coalition space.

Mine is a **manual linear approximation**: SHAP_i = weight_i × (actual_i - baseline_i).

The weights come from the Altman formula (X3 has weight 3.3). The baseline is a "neutral
grey-zone firm" at Z=2.40. For a linear model, this is exact — the linear coefficients
*are* the SHAP attribution weights.

Code: `risk_engine.py:explain_risk_drivers()`

---

**Q4: Explain your rate-shock scenario simulation methodology.**

1. Fetch the company's long-term debt balance.
2. Compute extra annual interest = debt_balance × (rate_shock_bps / 10,000).
3. Stressed EBIT = EBIT_base - extra_interest.
4. Re-run full Altman Z-Score with stressed EBIT.
5. Compare base_tier vs stressed_tier — flag tier migration.

Limitation I'd acknowledge: static debt balance, ignores refinancing and second-order effects.
For a real stress test you'd use a DCF with rate-sensitive discount rate.

Code: `routes/scenario.py`

---

**Q5: How did you implement portfolio VaR/CVaR?**

Historical simulation:
1. composite_risk_score/100 = proxy loss exposure per unit of capital.
2. Simulate 10,000 equally-weighted draws: N(score/100, vol × score/100).
3. VaR_95 = 95th percentile. CVaR_95 = mean of losses above VaR_95.

Seeded RNG (seed=42) for demo reproducibility. Limitation: ignores cross-company correlations.

Code: `routes/portfolio.py`

---

### SECTION 2: AI / RAG Architecture

---

**Q6: Why pgvector over Pinecone?**

1. **Colocation**: filing_chunks lives in the same Postgres instance. Single JOIN vs two round-trips.
2. **HNSW index**: O(log n) approximate nearest-neighbour. Sub-millisecond for <1000 chunks.
3. **Cost**: Zero — same free Supabase instance.

Trade-off: Pinecone scales better at millions of vectors.

---

**Q7: How do you ensure Claude doesn't hallucinate?**

Three layers:
1. System prompt: "Do NOT use outside knowledge not in the context."
2. Context injection: top-5 pgvector chunks + quantitative risk metrics always in the prompt.
3. Mandatory recommendation line parsing — defaults to "Monitor" (conservative) if ambiguous.

Code: `rag_engine.py:NARRATIVE_SYSTEM_PROMPT`, `generate_risk_narrative()`

---

**Q8: Why all-MiniLM-L6-v2 instead of OpenAI embeddings?**

- Cost: zero API cost, runs locally at ~10ms/chunk CPU inference.
- Latency: local vs 100-200ms API round-trip + rate limits.
- Quality: competitive MTEB retrieval scores for intra-company chunk matching.

Code: `rag_engine.py:get_embed_model()`

---

**Q9: Walk me through the pgvector retrieval query.**

```sql
SELECT chunk_text, chunk_index,
       1 - (embedding <=> :query_emb::vector) AS similarity
FROM filing_chunks
WHERE company_id = :company_id::uuid
ORDER BY embedding <=> :query_emb::vector
LIMIT :top_k
```

`<=>` is cosine distance. `1 - distance = similarity`. `WHERE company_id` scopes to
one company — never cross-company retrieval. HNSW makes this sub-millisecond.

Code: `rag_engine.py:retrieve_context()`

---

### SECTION 3: Engineering

---

**Q10: Explain your latency benchmark methodology. Why is it rigorous?**

`benchmark.py` fires 100 HTTP requests per tag:
- **Naive**: CACHE_ENABLED=false — recompute SHAP + LLM every call.
- **Optimized**: CACHE_ENABLED=true — LRU TTLCache (maxsize=200, TTL=5min).

Client-side wall-clock + server-side `X-Response-Time-Ms` both measured.
All timings logged to query_logs. `/latency-stats` computes p50/p95/p99 and improvement %.
Results saved to `benchmark_results.json` — physical evidence, not a claim.

---

**Q11: Why in-memory LRU cache rather than Redis?**

For a single-process Railway free tier deployment:
- Zero latency (in-process dict lookup, no network hop).
- Zero infrastructure complexity.
- Thread-safe for simple reads/writes.

Trade-off: doesn't survive restarts, doesn't share across multiple workers.
Redis is correct for horizontal scaling.

Code: `cache.py`

---

**Q12: How does your latency middleware avoid blocking requests?**

```python
start = time.perf_counter()
response = await call_next(request)
elapsed_ms = (time.perf_counter() - start) * 1000
```

DB write is try/excepted — failure logs a warning but doesn't propagate (graceful degradation).
`X-Response-Time-Ms` header added to every response for frontend display.

Code: `middleware/latency.py`

---

**Q13: How did you handle missing yfinance data?**

Three layers:
1. `safe_get()` tries multiple field names before returning None.
2. NaN guard: `isinstance(val, float) and np.isnan(val)` returns None.
3. Critical completeness check: skip entire record if total_assets is None/zero.
   Non-critical fields substituted with 0 in the formula.

Code: `ingest.py:fetch_company()`, `safe_get()`

---

### SECTION 4: Credit Risk Domain

---

**Q14: What's the significance of the Altman thresholds (1.81 / 2.99)?**

Derived by discriminant analysis on 33 bankrupt + 33 non-bankrupt US manufacturers (1946-1965).
Z > 2.99: near-zero 2-year default rate historically. Z ≤ 1.81: ~70% 2-year default probability.

Caveat: calibrated on 1960s US manufacturers. Asset-light tech companies may score lower
Z due to low asset turnover (X5) and negative retained earnings from buybacks (X2) — not actual distress.

---

**Q15: What's IFRS 9 and how is it relevant to your RAG corpus?**

IFRS 9 replaced IAS 39 with an Expected Credit Loss (ECL) model:
banks provision for expected future losses on Day 1, not just after objective evidence of default.

Three-stage: Stage 1 (12-month ECL) → Stage 2 (Lifetime ECL, significant deterioration) →
Stage 3 (Lifetime ECL, credit-impaired).

The RAG corpus includes IFRS 9 risk factor disclosures from 10-Ks — when an analyst
asks about credit risk management, retrieved chunks include actual IFRS 9 disclosures.

---

**Q16: Explain Distance-to-Default in plain English.**

Think of the company's assets as the underlying of an option. Debt is the strike.
If asset value falls below debt level, the company defaults (equity expires worthless).

DD = "How many standard deviations of asset movement away from default?"
DD = 3.0: catastrophic 3σ shock needed to default. DD = 0.5: barely solvent.
PD = N(-DD) converts to probability.

---

### SECTION 5: Design Decisions

---

**Q17: Why FastAPI over Django or Flask?**

1. **Async**: ASGI lets me await Anthropic + DB calls concurrently. Flask (WSGI) would block.
2. **Auto-generated OpenAPI**: Pydantic models → /docs Swagger UI automatically.
3. **Type safety**: all request/response validated at runtime via Pydantic.

---

**Q18: Why Supabase instead of local Postgres?**

- pgvector built-in (one click in Dashboard).
- Free hosted tier, instant HTTPS endpoint, no infrastructure to manage.
- Supavisor connection pooling available for production scale.

---

**Q19: How would you extend this to real-time credit surveillance?**

1. Railway cron job running `ingest.py` daily.
2. Alert engine: compare new vs previous risk_scores → webhook on tier migration.
3. News sentiment: embed financial news headlines → include in RAG context.
4. CDS spread integration: PD → implied spread via calibrated hazard rate model.

---

**Q20: What would you do differently with 6 months?**

1. **Iterative Merton**: KMV-style iterative solver instead of single-pass proxy.
2. **Labeled training data**: Moody's DRS defaults → proper XGBoost + TreeSHAP.
3. **Fine-tuned embeddings**: fine-tune MiniLM on SEC 10-K text for better retrieval.
4. **Backtesting**: validate recall on 2008-2009 and 2020 credit cycles.
5. **Basel III RWA calculator**: show how PD feeds into regulatory capital requirements.

---

## Quick Reference

| Concept | One-liner |
|---------|-----------|
| Altman Z | 5-factor discriminant; Z < 1.81 = Distress |
| Merton DTD | Equity as call option on assets; DD = σ-devs from default |
| SHAP | weight × (actual - baseline) for linear model |
| pgvector | Postgres cosine similarity; HNSW index O(log n) |
| IFRS 9 | ECL provisioning; 3-stage impairment model |
| VaR_95 | 95th pct loss; 5% chance of exceeding |
| CVaR_95 | Mean loss above VaR = Expected Shortfall |
| RAG | Retrieve filing context → ground LLM in it |
| LRU Cache | Evicts least-recently-used; TTL adds time expiry |
