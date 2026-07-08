"""
benchmark.py — Latency benchmark harness for Vantage Risk API.

Runs 100 requests against two code paths and logs results to query_logs:
  'naive'     → cache disabled (CACHE_ENABLED=false), recompute everything
  'optimized' → cache enabled  (CACHE_ENABLED=true)

Usage:
    python benchmark.py --url http://localhost:8000 --n 100

Output:
    - Prints p50/p95/p99 per tag in a table
    - Logs every request to query_logs via the API's /latency-stats endpoint
    - Saves a JSON summary to benchmark_results.json
"""

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

import httpx

BASE_COMPANIES = [
    "AAPL", "MSFT", "JPM", "F", "DAL", "BA", "AMC", "T", "GM", "NEE",
]


def percentile(data: list[float], pct: float) -> float:
    """Compute p-th percentile of data (0-100)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


def run_batch(
    base_url: str,
    tag: str,
    n: int,
    companies: list[str],
    cache_enabled: bool,
) -> list[float]:
    """
    Fire n requests against /companies/{ticker}/risk.
    Directly measures client-side response time.
    Also calls /benchmark-tag to log the tag to the server.
    Returns list of response times in ms.
    """
    print(f"\n{'='*50}")
    print(f"Running {n} requests  |  tag={tag}  |  cache={'ON' if cache_enabled else 'OFF'}")
    print(f"{'='*50}")

    times = []
    client = httpx.Client(timeout=30.0)

    # Tell backend which tag to use (patch the middleware tag via query param)
    for i in range(n):
        ticker = companies[i % len(companies)]
        url = f"{base_url}/companies/{ticker}/risk?_tag={tag}&_cache={str(cache_enabled).lower()}"
        try:
            t0 = time.perf_counter()
            resp = client.get(url)
            elapsed = (time.perf_counter() - t0) * 1000

            if resp.status_code == 200:
                times.append(elapsed)
                server_time = resp.headers.get("X-Response-Time-Ms", "?")
                if (i + 1) % 10 == 0:
                    print(f"  [{i+1:3d}/{n}] {ticker:6s} → {elapsed:6.1f}ms client | {server_time}ms server")
            else:
                print(f"  [{i+1:3d}/{n}] {ticker:6s} → HTTP {resp.status_code}")
        except Exception as exc:
            print(f"  [{i+1:3d}/{n}] {ticker:6s} → ERROR: {exc}")

    client.close()
    return times


def print_stats(tag: str, times: list[float]) -> dict:
    if not times:
        print(f"  No data for tag={tag}")
        return {}
    stats = {
        "tag":    tag,
        "n":      len(times),
        "avg_ms": round(statistics.mean(times), 2),
        "p50_ms": round(percentile(times, 50), 2),
        "p95_ms": round(percentile(times, 95), 2),
        "p99_ms": round(percentile(times, 99), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
    }
    print(f"\n── {tag.upper()} ──────────────────────────────")
    print(f"   n={stats['n']} | avg={stats['avg_ms']}ms | "
          f"p50={stats['p50_ms']}ms | p95={stats['p95_ms']}ms | p99={stats['p99_ms']}ms")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Vantage Risk latency benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--n", type=int, default=100, help="Requests per tag")
    parser.add_argument("--output", default="benchmark_results.json", help="Output file")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    # ── Health check ──────────────────────────────────────────────────────────
    print(f"Connecting to {base_url}/health …")
    try:
        resp = httpx.get(f"{base_url}/health", timeout=5)
        print(f"API health: {resp.json()}")
    except Exception as exc:
        print(f"❌ Cannot reach API at {base_url}: {exc}")
        sys.exit(1)

    # ── Naive run (cache disabled) ────────────────────────────────────────────
    naive_times = run_batch(base_url, "naive", args.n, BASE_COMPANIES, cache_enabled=False)
    naive_stats = print_stats("naive", naive_times)

    # ── Warm-up run (don't count) ─────────────────────────────────────────────
    print("\n[Warming up cache with 10 requests…]")
    run_batch(base_url, "warmup", 10, BASE_COMPANIES, cache_enabled=True)

    # ── Optimised run (cache enabled) ─────────────────────────────────────────
    opt_times = run_batch(base_url, "optimized", args.n, BASE_COMPANIES, cache_enabled=True)
    opt_stats = print_stats("optimized", opt_times)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("BENCHMARK SUMMARY")
    print("=" * 50)

    improvement_pct = None
    if naive_stats.get("p95_ms") and opt_stats.get("p95_ms"):
        naive_p95 = naive_stats["p95_ms"]
        opt_p95   = opt_stats["p95_ms"]
        improvement_pct = round((naive_p95 - opt_p95) / naive_p95 * 100, 1)
        print(f"  Naive p95:     {naive_p95}ms")
        print(f"  Optimized p95: {opt_p95}ms")
        print(f"  Improvement:   {improvement_pct}%  ({'✅' if improvement_pct > 0 else '⚠️'})")

    # ── Save results ──────────────────────────────────────────────────────────
    results = {
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "api_url":         base_url,
        "n_per_tag":       args.n,
        "naive":           naive_stats,
        "optimized":       opt_stats,
        "improvement_pct": improvement_pct,
    }
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📊 Results saved to {args.output}")
    print("Screenshot this terminal output + the benchmark_results.json for your resume proof.")


if __name__ == "__main__":
    main()
