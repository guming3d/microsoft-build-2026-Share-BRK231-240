"""
Performance benchmark for Web IQ v3.

Measures end-to-end latency percentiles (p50/p90/p95/p99) for a chosen endpoint
and compares p95 against the documented target of 164 ms. Optional concurrency
lets you probe throughput / rate-limit (429) behaviour.

Requires live credentials.

Examples:
    python benchmark.py --endpoint web -n 50
    python benchmark.py --endpoint web -n 100 --concurrency 8
    python benchmark.py --endpoint browse --url https://news.microsoft.com/source/
"""

from __future__ import annotations

import sys
import time
import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from webiq_client import WebIQError, WebIQValidationError, client_from_env

DOC_P95_MS = 164.0  # documented target

QUERIES = [
    "latest trends in LLM RAG", "microsoft build 2026 announcements",
    "azure ai foundry pricing", "vector database benchmarks 2026",
    "quantum computing breakthroughs", "best practices prompt engineering",
    "kubernetes autoscaling guide", "renewable energy investment news",
    "stock market outlook today", "open source agent frameworks",
]


def call(client, endpoint: str, query: str, url: str):
    if endpoint == "web":
        return client.web(query, max_results=10, content_format="passage", max_length=2000)
    if endpoint == "news":
        return client.news(query, max_results=10, max_length=2000)
    if endpoint == "images":
        return client.images(query, max_results=10)
    if endpoint == "videos":
        return client.videos(query, max_results=10)
    if endpoint == "browse":
        return client.browse(url, max_length=2000, content_format="text")
    if endpoint == "classic":
        return client.classic(query, max_results_web=5, max_length=1000)
    raise ValueError(f"unknown endpoint: {endpoint}")


def pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="web",
                    choices=["web", "news", "images", "videos", "browse", "classic"])
    ap.add_argument("-n", "--iterations", type=int, default=30)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--warmup", type=int, default=2, help="discarded warmup calls")
    ap.add_argument("--url", default="https://news.microsoft.com/source/")
    args = ap.parse_args()

    try:
        # Disable client retries so we measure raw latency and *see* 429s.
        client = client_from_env(validate=True)
        client.max_retries = 0
    except WebIQValidationError as exc:
        print(f"Cannot build client: {exc}")
        print("Set WEBIQ_API_KEY (or Entra vars) first.")
        return 2

    print(f"Benchmark: endpoint={args.endpoint}  iterations={args.iterations}  "
          f"concurrency={args.concurrency}  warmup={args.warmup}")

    # Warmup (not measured) - primes TLS/connection pool.
    for i in range(args.warmup):
        try:
            call(client, args.endpoint, QUERIES[i % len(QUERIES)], args.url)
        except Exception:
            pass

    latencies: list[float] = []
    status_counts: dict[str, int] = {}
    rate_limited = 0
    errors = 0

    def one(i: int):
        q = QUERIES[i % len(QUERIES)]
        try:
            r = call(client, args.endpoint, q, args.url)
            return ("200", r.elapsed_ms)
        except WebIQError as exc:
            return (str(exc.status), None)
        except Exception as exc:  # network etc.
            return (f"EXC:{type(exc).__name__}", None)

    wall_start = time.perf_counter()
    if args.concurrency <= 1:
        for i in range(args.iterations):
            status, ms = one(i)
            status_counts[status] = status_counts.get(status, 0) + 1
            if ms is not None:
                latencies.append(ms)
            elif status == "429":
                rate_limited += 1
            else:
                errors += 1
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futs = [pool.submit(one, i) for i in range(args.iterations)]
            for fut in as_completed(futs):
                status, ms = fut.result()
                status_counts[status] = status_counts.get(status, 0) + 1
                if ms is not None:
                    latencies.append(ms)
                elif status == "429":
                    rate_limited += 1
                else:
                    errors += 1
    wall = time.perf_counter() - wall_start

    print("\n--- Status codes ---")
    for code, n in sorted(status_counts.items()):
        print(f"  {code}: {n}")

    if latencies:
        print("\n--- Latency (ms), successful calls ---")
        print(f"  count : {len(latencies)}")
        print(f"  min   : {min(latencies):8.1f}")
        print(f"  mean  : {statistics.fmean(latencies):8.1f}")
        print(f"  p50   : {pct(latencies, 50):8.1f}")
        print(f"  p90   : {pct(latencies, 90):8.1f}")
        p95 = pct(latencies, 95)
        print(f"  p95   : {p95:8.1f}   (doc target {DOC_P95_MS:.0f} ms -> "
              f"{'MEETS' if p95 <= DOC_P95_MS else 'ABOVE'})")
        print(f"  p99   : {pct(latencies, 99):8.1f}")
        print(f"  max   : {max(latencies):8.1f}")
        print(f"\n  throughput: {len(latencies) / wall:6.2f} req/s over {wall:.1f}s wall")
        if rate_limited:
            print(f"  NOTE: {rate_limited} request(s) were rate-limited (429).")
    else:
        print("\nNo successful calls to measure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
