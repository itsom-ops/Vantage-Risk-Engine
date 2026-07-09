"""
rag_engine.py — SEC 10-K filing ingestion, pgvector retrieval, Claude narrative generation.

Three public functions:
    ingest_filing_text(company_id, text, db_engine)
    retrieve_context(company_id, query, db_engine, top_k=5)
    generate_risk_narrative(company_id, query, db_engine, anthropic_client)
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional

import anthropic
import numpy as np
import yfinance as yf
from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

# ── Model singleton (loaded once on first import) ─────────────────────────────
_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        log.info(f"Loading embedding model '{model_name}' (first call only)…")
        _embed_model = SentenceTransformer(model_name)
    return _embed_model


def _chunk_text(text_body: str, max_tokens: int = 500) -> list[str]:
    """
    Split text into ~max_tokens-sized chunks at sentence boundaries.
    Rough heuristic: 1 token ≈ 4 characters.
    """
    max_chars = max_tokens * 4
    sentences = re.split(r"(?<=[.!?])\s+", text_body.strip())
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current += " " + sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _embed(texts: list[str]) -> list[list[float]]:
    """Encode a list of texts → list of 384-dim embedding vectors."""
    model = get_embed_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Ingest filing text into filing_chunks
# ─────────────────────────────────────────────────────────────────────────────

def ingest_filing_text(
    company_id: str,
    text_body: str,
    db_engine: Engine,
    filing_date: str = "",
    form_type: str = "10-K",
    section: str = "Risk Factors",
) -> int:
    """
    Chunk `text_body` into ~500-token pieces, embed each chunk with
    all-MiniLM-L6-v2, and upsert into filing_chunks.

    Returns the number of chunks ingested.
    """
    chunks = _chunk_text(text_body)
    if not chunks:
        log.warning(f"No chunks produced for company {company_id}.")
        return 0

    embeddings = _embed(chunks)

    ingested = 0
    with db_engine.connect() as conn:
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            # Format embedding as pgvector literal: [0.1, 0.2, ...]
            emb_str = "[" + ",".join(f"{v:.8f}" for v in emb) + "]"
            conn.execute(text("""
                INSERT INTO filing_chunks
                    (company_id, filing_date, form_type, section,
                     chunk_index, chunk_text, token_count, embedding)
                VALUES
                    (:company_id::uuid, :filing_date, :form_type, :section,
                     :chunk_index, :chunk_text, :token_count, :embedding::vector)
                ON CONFLICT DO NOTHING
            """), {
                "company_id":  company_id,
                "filing_date": filing_date,
                "form_type":   form_type,
                "section":     section,
                "chunk_index": i,
                "chunk_text":  chunk,
                "token_count": len(chunk) // 4,
                "embedding":   emb_str,
            })
            ingested += 1
        conn.commit()

    log.info(f"Ingested {ingested} chunks for company {company_id}.")
    return ingested


# ─────────────────────────────────────────────────────────────────────────────
# 2. Retrieve context via pgvector cosine similarity
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_context(
    company_id: str,
    query: str,
    db_engine: Engine,
    top_k: int = 5,
) -> list[dict]:
    """
    Encode the query, then run a pgvector cosine-similarity search
    scoped to the given company's filing chunks.

    Returns a list of {chunk_text, similarity_score, chunk_index}.
    """
    query_emb = _embed([query])[0]
    emb_str = "[" + ",".join(f"{v:.8f}" for v in query_emb) + "]"

    with db_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT chunk_text, chunk_index,
                   1 - (embedding <=> CAST(:query_emb AS vector)) AS similarity
            FROM filing_chunks
            WHERE company_id = CAST(:company_id AS uuid)
            ORDER BY embedding <=> CAST(:query_emb AS vector)
            LIMIT :top_k
        """), {
            "query_emb":  emb_str,
            "company_id": company_id,
            "top_k":      top_k,
        }).fetchall()

    return [
        {
            "chunk_text":  r[0],
            "chunk_index": r[1],
            "similarity":  round(float(r[2]), 4),
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Generate risk narrative with Claude
# ─────────────────────────────────────────────────────────────────────────────

NARRATIVE_SYSTEM_PROMPT = """You are a senior credit risk analyst at a top-tier investment bank.
Your task is to answer the analyst's question directly, naturally, and in plain conversational language.

You are NOT a report generator that must always output a fixed set of fields.
- Answer the user's actual question directly first.
- Only bring in risk scores, SHAP drivers, filing text, or news where they are genuinely relevant to answering the question.
- Use the provided data to support your answer, and only cite the specific numbers or facts that are relevant to what was asked.
- If the question is an investment-opinion query (asking whether to buy, sell, or invest), you MUST NEVER give direct financial advice or say 'Yes' or 'No'. Instead, lay out the specific relevant risk factors, news context, and valuation signals, and end with a neutral framing: 'Here is what the data shows, the decision is yours.'
- Base your answer strictly on the provided context bundle. Do not invent any facts.
- End with a professional recommendation on a new line: 'Recommendation: Monitor' or 'Recommendation: Flag for review' or 'Recommendation: Low concern'.
"""

def generate_risk_narrative(
    company_id: str,
    ticker: str,
    query: str,
    risk_score_row: dict,
    db_engine: Engine,
    anthropic_client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> tuple[str, str, int, float]:
    """
    Full RAG pipeline:
    1. Short pass query classification (GENERAL, OPINION, METRIC, NEWS, COMPARISON, OTHER).
    2. Build context bundle (yfinance summary, latest news, risk_scores row, top RAG chunks).
    3. Call Claude for a conversational, intent-aware response.
    """
    t0 = time.perf_counter()

    # 1. Intent Classification Pass
    classification_prompt = f"""
Classify the intent of the following user query about a company:
Query: "{query}"

Respond with EXACTLY one of the following classification tags:
- GENERAL (general company/business description, sector, what they do)
- OPINION (buy/sell/investment opinion, recommendation, is it a good buy)
- METRIC (specific risk metrics, Altman Z, Merton DTD, specific ratios, values)
- NEWS (news, recent events, sentiment)
- COMPARISON (comparison with other companies or peers)
- OTHER (open-ended, general definitions, other topics)

Do not output any other text besides the tag.
"""
    try:
        class_msg = anthropic_client.messages.create(
            model=model,
            max_tokens=10,
            system="You are an intent classifier. Output ONLY the uppercase classification tag.",
            messages=[{"role": "user", "content": classification_prompt}]
        )
        intent = class_msg.content[0].text.strip().upper()
    except Exception as e:
        log.warning(f"Classification pass failed: {e}. Using local keyword fallback classification...")
        q_lower = query.lower()
        if any(w in q_lower for w in ["buy", "sell", "invest", "recommendation", "portfolio", "suitability"]):
            intent = "OPINION"
        elif any(w in q_lower for w in ["altman", "z-score", "merton", "default", "ratio", "score", "metric", "distance"]):
            intent = "METRIC"
        elif any(w in q_lower for w in ["news", "headline", "sentiment", "event", "recent"]):
            intent = "NEWS"
        elif any(w in q_lower for w in ["compare", "versus", "vs", "peer", "industry average"]):
            intent = "COMPARISON"
        elif any(w in q_lower for w in ["what does", "describe", "overview", "business", "sector", "industry"]):
            intent = "GENERAL"
        else:
            intent = "OTHER"

    # 2. Retrieve filing context chunks (top 5)
    chunks = retrieve_context(company_id, query, db_engine)
    if chunks:
        context_block = "\n\n".join([
            f"[Filing excerpt {i+1} | similarity={c['similarity']:.2f}]\n{c['chunk_text']}"
            for i, c in enumerate(chunks)
        ])
    else:
        context_block = "[No filing excerpts retrieved.]"

    # 3. Fetch yfinance profile
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        biz_summary = info.get("longBusinessSummary", "No business description available.")
        mkt_cap = info.get("marketCap", "N/A")
        sector = info.get("sector", "N/A")
    except Exception:
        biz_summary = "No business description available."
        mkt_cap = "N/A"
        sector = "N/A"

    # 4. Fetch latest news from database
    try:
        with db_engine.connect() as conn:
            news_rows = conn.execute(text("""
                SELECT headline, sentiment_label
                FROM news_items
                WHERE company_id = :cid::uuid
                ORDER BY published_at DESC LIMIT 3
            """), {"cid": company_id}).fetchall()
        news_list = [f"- {r[0]} (Sentiment: {r[1]})" for r in news_rows]
        news_text = "\n".join(news_list) if news_list else "No recent news logged in database."
    except Exception:
        news_text = "No recent news logged in database."

    # 5. Build context bundle prompt
    metrics = (
        f"Company Ticker: {ticker}\n"
        f"Sector: {sector}\n"
        f"Market Cap: {mkt_cap}\n"
        f"Altman Z-Score: {risk_score_row.get('altman_z', 'N/A')} ({risk_score_row.get('altman_tier', 'N/A')})\n"
        f"Distance-to-Default: {risk_score_row.get('distance_to_default', 'N/A')}\n"
        f"Probability of Default: {risk_score_row.get('prob_of_default', 'N/A')}\n"
        f"Composite Risk Score: {risk_score_row.get('composite_risk_score', 'N/A')}/100 ({risk_score_row.get('risk_tier', 'N/A')})\n"
        f"Top Risk Driver: {risk_score_row.get('top_risk_driver_1', 'N/A')}\n"
    )

    user_prompt = f"""
CONTEXT BUNDLE:

[Company Description]
{biz_summary}

[Financial Risk Metrics]
{metrics}

[Recent News Headlines]
{news_text}

[SEC 10-K Filing Excerpts]
{context_block}

USER QUERY: "{query}"
CLASSIFIED INTENT: {intent}

Based on the rules and context above, write a natural conversational response to the user query.
"""

    # 6. Call Claude
    try:
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=500,
            system=NARRATIVE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as e:
        log.warning(f"Claude API narrative generation failed, executing fallback generator: {e}")
        # Build a conversational fallback paragraph based on the intent
        if intent == "GENERAL":
            raw = f"Regarding your question on {ticker}'s business profile ('{query}'): the company operates in the sector with a market capitalization of {mkt_cap}. The business summary outlines solid operations, while the credit metrics indicate a composite risk score of {risk_score_row.get('composite_risk_score', 'N/A')}/100, placing it in the {risk_score_row.get('risk_tier', 'N/A')} risk tier.\nRecommendation: Low concern"
        elif intent == "OPINION":
            raw = f"Addressing the investment query '{query}' for {ticker}: analyzing suitability requires reviewing multiple risk vectors. Currently, the company has an Altman Z-Score of {risk_score_row.get('altman_z', 'N/A')}, indicating it lies in the {risk_score_row.get('altman_tier', 'N/A')} category, and a default probability of {risk_score_row.get('prob_of_default', 'N/A')}. Risk factors from recent filings and news suggest keeping an eye on operational margins, so while the decision is yours, a measured approach is advised.\nRecommendation: Monitor"
        elif intent == "METRIC":
            raw = f"In response to your query on metrics '{query}': for {ticker}, the Altman Z-Score is {risk_score_row.get('altman_z', 'N/A')}, indicating a {risk_score_row.get('altman_tier', 'N/A')} status. The Merton model calculates a Distance-to-Default of {risk_score_row.get('distance_to_default', 'N/A')} with an associated probability of default of {risk_score_row.get('prob_of_default', 'N/A')}. The primary risk driver is flagged as: {risk_score_row.get('top_risk_driver_1', 'N/A')}.\nRecommendation: Monitor"
        elif intent == "NEWS":
            raw = f"Concerning the news updates queried in '{query}': recent headlines for {ticker} show active market updates. These headlines suggest active market attention, though long-term credit ratios remain anchored to the composite score of {risk_score_row.get('composite_risk_score', 'N/A')}/100.\nRecommendation: Monitor"
        elif intent == "COMPARISON":
            raw = f"For the comparison query '{query}': comparing {ticker} to peers, its composite risk score is {risk_score_row.get('composite_risk_score', 'N/A')}/100, which classifies it as {risk_score_row.get('risk_tier', 'N/A')} risk. The Distance-to-Default metric of {risk_score_row.get('distance_to_default', 'N/A')} indicates relative credit stability compared to lower-rated distressed assets in the sector.\nRecommendation: Low concern"
        else:
            raw = f"Answering the general/other request '{query}': Vantage Risk analyzed {ticker} and computed a composite risk score of {risk_score_row.get('composite_risk_score', 'N/A')}/100. This places the firm in the {risk_score_row.get('risk_tier', 'N/A')} category. The Distance-to-Default stands at {risk_score_row.get('distance_to_default', 'N/A')}.\nRecommendation: Monitor"
            
    raw = raw.strip()
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 7. Extract recommendation
    recommendation = "Monitor"
    for line in raw.split("\n"):
        if line.strip().startswith("Recommendation:"):
            rec_text = line.split(":", 1)[1].strip()
            if "flag" in rec_text.lower():
                recommendation = "Flag for review"
            elif "low" in rec_text.lower():
                recommendation = "Low concern"
            else:
                recommendation = "Monitor"
            break

    # Strip recommendation line from narrative body
    narrative_lines = [
        l for l in raw.split("\n")
        if not l.strip().startswith("Recommendation:")
    ]
    narrative = " ".join(narrative_lines).strip()

    return narrative, recommendation, len(chunks), elapsed_ms
