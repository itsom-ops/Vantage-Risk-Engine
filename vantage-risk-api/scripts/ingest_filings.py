"""
scripts/ingest_filings.py — Pull 10-K risk factor text from SEC EDGAR
and load into filing_chunks via the RAG engine.

Usage:
    python scripts/ingest_filings.py          # all tickers
    python scripts/ingest_filings.py AAPL BA  # specific tickers

SEC EDGAR full-text search is free, no API key needed.
Rate limit: 10 req/sec per EDGAR guidelines (we sleep 0.12s between calls).
"""

import sys
import time
import logging
import requests
from pathlib import Path

# Allow imports from parent dirs
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vantage-risk-pipeline"))

from db import engine
from rag_engine import ingest_filing_text
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

EDGAR_HEADERS = {
    "User-Agent": "VantageRisk research@vantagerisk.com",  # required by SEC
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}
EDGAR_SUBMISSION_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
EDGAR_FILING_URL     = "https://www.sec.gov/Archives/edgar/full-index/"


def get_cik(ticker: str) -> str | None:
    """Resolve ticker → CIK via SEC EDGAR company_tickers.json."""
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "VantageRisk research@vantagerisk.com"},
            timeout=10,
        )
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"])
    except Exception as exc:
        log.warning(f"CIK lookup failed for {ticker}: {exc}")
    return None


def get_latest_10k_accession(cik: str) -> tuple[str, str] | tuple[None, None]:
    """Return (accession_number, filing_date) of the most recent 10-K."""
    try:
        url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates   = filings.get("filingDate", [])
        for form, acc, date in zip(forms, accessions, dates):
            if form == "10-K":
                return acc, date
    except Exception as exc:
        log.warning(f"10-K lookup failed for CIK {cik}: {exc}")
    return None, None


def fetch_risk_factors_text(cik: str, accession: str) -> str | None:
    """
    Download the 10-K filing index, find the primary document,
    and extract the Risk Factors section (Item 1A) via text search.
    """
    acc_clean = accession.replace("-", "")
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/"
        f"{accession}-index.json"
    )
    try:
        resp = requests.get(
            index_url,
            headers={"User-Agent": "VantageRisk research@vantagerisk.com"},
            timeout=15,
        )
        index = resp.json()
        files = index.get("directory", {}).get("item", [])

        # Find the primary HTML/HTM document
        primary = None
        for f in files:
            name = f.get("name", "")
            if name.endswith((".htm", ".html")) and "10-k" in name.lower():
                primary = name
                break
        if not primary and files:
            # Fall back to first htm file
            for f in files:
                if f.get("name", "").endswith((".htm", ".html")):
                    primary = f["name"]
                    break

        if not primary:
            log.warning(f"No primary document found in {accession} index")
            return None

        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{primary}"
        )
        doc_resp = requests.get(
            doc_url,
            headers={"User-Agent": "VantageRisk research@vantagerisk.com"},
            timeout=30,
        )

        # Extract text between "Item 1A" and "Item 1B" (or "Item 2")
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []
                self._skip_tags = {"script", "style"}
                self._current_tag = None

            def handle_starttag(self, tag, attrs):
                self._current_tag = tag

            def handle_data(self, data):
                if self._current_tag not in self._skip_tags:
                    self.text_parts.append(data)

        parser = TextExtractor()
        parser.feed(doc_resp.text)
        full_text = " ".join(parser.text_parts)

        # Find Risk Factors section
        import re
        pattern = re.compile(
            r"(item\s+1a[\.\-\s]*risk\s+factors)(.*?)(item\s+1b|item\s+2|unresolved\s+staff)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(full_text)
        if match:
            risk_text = match.group(2).strip()
            # Limit to first 15,000 chars (plenty for RAG context)
            return risk_text[:15_000]
        else:
            log.warning("Could not find Item 1A section — using first 8000 chars of document.")
            return full_text[:8_000]

    except Exception as exc:
        log.warning(f"Filing text fetch failed for {accession}: {exc}")
        return None


def ingest_ticker(ticker: str) -> bool:
    """Full pipeline for one ticker: CIK → 10-K accession → risk text → chunks."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id::text FROM companies WHERE ticker = :t"),
            {"t": ticker}
        ).fetchone()

    if not row:
        log.warning(f"  {ticker}: not in companies table — run ingest.py first.")
        return False

    company_id = row[0]
    log.info(f"  {ticker} ({company_id[:8]}…) — resolving CIK…")

    cik = get_cik(ticker)
    if not cik:
        log.warning(f"  {ticker}: CIK not found.")
        return False

    time.sleep(0.15)  # EDGAR rate limit: 10 req/sec
    accession, filing_date = get_latest_10k_accession(cik)
    if not accession:
        log.warning(f"  {ticker}: no 10-K found.")
        return False

    log.info(f"  {ticker}: fetching 10-K {accession} ({filing_date})…")
    time.sleep(0.15)
    text_body = fetch_risk_factors_text(cik, accession)
    if not text_body or len(text_body) < 200:
        log.warning(f"  {ticker}: risk factors text too short ({len(text_body or '')} chars).")
        return False

    n_chunks = ingest_filing_text(
        company_id   = company_id,
        text_body    = text_body,
        db_engine    = engine,
        filing_date  = filing_date or "",
        form_type    = "10-K",
        section      = "Risk Factors",
    )
    log.info(f"  ✅ {ticker}: {n_chunks} chunks ingested.")
    return True


if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else [
        "AAPL", "MSFT", "JPM", "F", "DAL", "BA", "AMC", "T", "GM", "NEE",
        "XOM", "PARA", "CCL", "VFC", "WBA",
    ]

    log.info(f"Filing ingestion starting — {len(tickers)} tickers")
    ok, fail = 0, 0
    for ticker in tickers:
        log.info(f"\n[{tickers.index(ticker)+1}/{len(tickers)}] {ticker}")
        if ingest_ticker(ticker):
            ok += 1
        else:
            fail += 1
        time.sleep(0.5)  # EDGAR rate limit buffer

    log.info(f"\n{'─'*40}")
    log.info(f"Done: {ok} succeeded | {fail} failed")
