"""
cache.py — In-memory LRU cache with TTL for risk scores and insight responses.

Used in two modes:
  'live'      → cache enabled (normal operation, TTL=5min)
  'naive'     → cache disabled (benchmark baseline path)
  'optimized' → cache enabled (benchmark optimized path)

The benchmark script toggles CACHE_ENABLED env var between runs.
"""

import hashlib
import os
from cachetools import TTLCache

# Toggle to disable caching for the 'naive' benchmark path
CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# Risk score cache: 200 entries, 5-minute TTL
risk_cache: TTLCache = TTLCache(maxsize=200, ttl=300)

# Insight/RAG cache: 100 entries, 5-minute TTL
insight_cache: TTLCache = TTLCache(maxsize=100, ttl=300)


def make_cache_key(prefix: str, *parts: str) -> str:
    """Hash multiple parts into a short cache key."""
    raw = f"{prefix}:" + ":".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def is_cache_enabled() -> bool:
    return CACHE_ENABLED
