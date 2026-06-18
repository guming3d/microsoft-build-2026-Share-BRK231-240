"""
Q4 - Cold-start vs warm latency (the code-testable part of the performance question).

The "is 164ms an SLA?" and "are there regional endpoints?" parts are contractual /
infrastructure questions and are summarized in the PPT instead.

What this measures:
  For each endpoint we create a BRAND-NEW client (new requests.Session => new TCP/TLS
  handshake) and time the very first call (COLD). Then we fire N more calls on the same
  warmed connection (WARM). We repeat the cold measurement several times with a fresh
  client each round to get a stable cold estimate, and report the cold-vs-warm penalty.

Usage:
  python test_q4_coldstart.py
  python test_q4_coldstart.py --rounds 5 --warm 5
"""
from __future__ import annotations
import argparse
import os
import statistics
from webiq_client import WebIQClient, DEFAULT_BASE_URL


def fresh_client() -> WebIQClient:
    # New WebIQClient => new requests.Session => new connection pool (cold).
    return WebIQClient(
        api_key=os.environ.get("WEBIQ_API_KEY"),
        base_url=os.environ.get("WEBIQ_BASE_URL", DEFAULT_BASE_URL),
        validate=False,
    )


def call(client: WebIQClient, endpoint: str):
    if endpoint == "web":
        return client.web("Microsoft Build 2026", max_results=10)
    if endpoint == "news":
        return client.news("Microsoft Build 2026", max_results=10)
    if endpoint == "browse":
        return client.browse("https://www.microsoft.com")
    raise ValueError(endpoint)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=5, help="cold rounds (fresh client each)")
    ap.add_argument("--warm", type=int, default=5, help="warm calls per round")
    ap.add_argument("--endpoints", nargs="+", default=["web", "news", "browse"])
    args = ap.parse_args()

    print(f"Cold-start probe: rounds={args.rounds}  warm-calls/round={args.warm}")
    print(f"(each round = new client/session for cold, then {args.warm} warm calls)\n")

    for ep in args.endpoints:
        cold_samples: list[float] = []
        warm_samples: list[float] = []
        for _ in range(args.rounds):
            c = fresh_client()
            cold_samples.append(call(c, ep).elapsed_ms)          # first call = cold
            for _ in range(args.warm):
                warm_samples.append(call(c, ep).elapsed_ms)      # reuse connection = warm

        cold_med = statistics.median(cold_samples)
        warm_med = statistics.median(warm_samples)
        penalty = cold_med - warm_med
        ratio = (cold_med / warm_med) if warm_med else float("nan")

        print(f"=== {ep} ===")
        print(f"  cold (first call, n={len(cold_samples):>2}):  "
              f"median={cold_med:7.1f} ms   min={min(cold_samples):7.1f}   max={max(cold_samples):7.1f}")
        print(f"  warm (reused conn, n={len(warm_samples):>2}):  "
              f"median={warm_med:7.1f} ms   min={min(warm_samples):7.1f}   max={max(warm_samples):7.1f}")
        print(f"  cold-start penalty: +{penalty:.1f} ms  ({ratio:.1f}x warm)\n")

    print("Interpretation: a large cold/warm ratio means connection reuse (keep-alive,")
    print("pooled sessions) is essential to approach the documented latency targets.")


if __name__ == "__main__":
    main()
