"""
Q1 - Result determinism & freshness.

Answers (via live calls):
  A. Cache TTL          - re-query the same term over increasing wait intervals
                          and measure when (if) the result set changes.
  B. freshness filter   - does news honor a `freshness` field (day/week/month/year)?
                          The typed client doesn't expose it, so we raw-probe via _post.
  C. force-fresh probe  - do any cache-busting body params change the response?

Usage:
  python test_q1_freshness.py                 # full run (~5 min cache probe)
  python test_q1_freshness.py --max-seconds 120
  python test_q1_freshness.py --skip-ttl      # only freshness + force-fresh
"""
from __future__ import annotations
import argparse
import time
from webiq_client import client_from_env


def news_urls(data: dict) -> list[str]:
    return [i.get("url", "") for i in data.get("newsResults", [])]


def jaccard(a: set, b: set) -> float:
    u = len(a | b)
    return (len(a & b) / u) if u else 1.0


# --------------------------------------------------------------------------- #
def probe_cache_ttl(client, query: str, max_seconds: int) -> None:
    print("\n" + "=" * 70)
    print(f"A. CACHE TTL  -  query='{query}'  budget={max_seconds}s")
    print("=" * 70)

    base = client.news(query, max_results=20)
    base_set = set(news_urls(base.data))
    print(f"  t=0s      baseline: {len(base_set)} results  ({base.elapsed_ms:.0f} ms)")

    # cumulative checkpoints, capped at the budget
    checkpoints = [c for c in (30, 60, 120, 300, 600) if c <= max_seconds]
    prev = 0
    changed_at = None
    for t in checkpoints:
        time.sleep(t - prev)
        prev = t
        r = client.news(query, max_results=20)
        cur = set(news_urls(r.data))
        sim = jaccard(base_set, cur)
        added = len(cur - base_set)
        dropped = len(base_set - cur)
        flag = "IDENTICAL" if sim == 1.0 else f"CHANGED (+{added}/-{dropped})"
        print(f"  t={t:>4}s   sim-to-baseline={sim:5.1%}  {flag}  ({r.elapsed_ms:.0f} ms)")
        if sim < 1.0 and changed_at is None:
            changed_at = t

    print("\n  --- verdict ---")
    if changed_at is None:
        print(f"  Result set STABLE for the full {prev}s window -> cache TTL >= {prev}s.")
    else:
        print(f"  Result set first changed at t={changed_at}s -> cache TTL ~< {changed_at}s.")


# --------------------------------------------------------------------------- #
def probe_freshness(client, query: str) -> None:
    print("\n" + "=" * 70)
    print(f"B. FRESHNESS FILTER (news, raw _post)  -  query='{query}'")
    print("=" * 70)

    levels = [None, "day", "week", "month", "year"]
    sets: dict[str, set] = {}
    for lvl in levels:
        body = {"query": query, "maxResults": 20}
        if lvl is not None:
            body["freshness"] = lvl
        try:
            r = client._post("/search/news", body)
            urls = set(news_urls(r.data))
            sets[str(lvl)] = urls
            print(f"  freshness={str(lvl):<6} -> HTTP 200, {len(urls)} results  ({r.elapsed_ms:.0f} ms)")
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status", "?")
            sets[str(lvl)] = set()
            print(f"  freshness={str(lvl):<6} -> rejected (HTTP {status})  {exc}")

    print("\n  --- pairwise overlap (does the filter actually narrow results?) ---")
    order = ["day", "week", "month", "year", "None"]
    present = [k for k in order if sets.get(k)]
    base = sets.get("None", set())
    for k in present:
        if k == "None":
            continue
        s = sets[k]
        subset = "yes" if s and s <= base else "no"
        print(f"  {k:<6} vs None: overlap={jaccard(s, base):5.1%}  subset-of-None={subset}  size={len(s)}")

    distinct = len({frozenset(s) for s in sets.values() if s})
    print("\n  --- verdict ---")
    if distinct <= 1:
        print("  All freshness levels returned the SAME set -> freshness is IGNORED / no-op.")
    else:
        print(f"  {distinct} distinct result sets across levels -> freshness DOES affect results.")


# --------------------------------------------------------------------------- #
def probe_force_fresh(client, query: str) -> None:
    print("\n" + "=" * 70)
    print(f"C. FORCE-FRESH / CACHE-BUST PROBE (raw _post)  -  query='{query}'")
    print("=" * 70)

    base = client.news(query, max_results=20)
    base_set = set(news_urls(base.data))

    candidates = [
        {"cache": False}, {"noCache": True}, {"freshCache": True},
        {"bypassCache": True}, {"fresh": True}, {"liveCrawl": "fallback"},
    ]
    for extra in candidates:
        body = {"query": query, "maxResults": 20, **extra}
        key = list(extra.keys())[0]
        try:
            r = client._post("/search/news", body)
            cur = set(news_urls(r.data))
            sim = jaccard(base_set, cur)
            effect = "DIFFERENT results" if sim < 1.0 else "no change"
            print(f"  +{key:<12} -> HTTP 200  sim={sim:5.1%}  ({effect})")
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status", "?")
            print(f"  +{key:<12} -> rejected (HTTP {status})")

    print("\n  --- verdict ---")
    print("  Any 'DIFFERENT results' above = a working cache-bust param; otherwise none exists.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="Microsoft Build 2026")
    ap.add_argument("--max-seconds", type=int, default=300)
    ap.add_argument("--skip-ttl", action="store_true")
    args = ap.parse_args()

    client = client_from_env()
    if not args.skip_ttl:
        probe_cache_ttl(client, args.query, args.max_seconds)
    probe_freshness(client, "artificial intelligence")
    probe_force_fresh(client, args.query)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
