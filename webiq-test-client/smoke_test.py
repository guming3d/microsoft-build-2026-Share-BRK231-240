"""
Smoke test: call every Web IQ v3 endpoint once and print status, latency,
trace id, and a tiny sample of the results. Requires live credentials.

Run:
    python smoke_test.py
    python smoke_test.py --query "latest trends in LLM RAG"
"""

from __future__ import annotations

import sys
import argparse

from webiq_client import WebIQError, WebIQValidationError, client_from_env


def _first(items, *keys):
    if not items:
        return "(no results)"
    item = items[0]
    return " | ".join(str(item.get(k, ""))[:70] for k in keys)


def run_case(name: str, fn, summarize) -> bool:
    try:
        resp = fn()
        sample = summarize(resp)
        print(f"[OK ] {name:<10} {resp.elapsed_ms:7.1f} ms  attempts={resp.attempts}  "
              f"trace={resp.trace_id}")
        print(f"       {sample}")
        return True
    except WebIQError as exc:
        print(f"[ERR] {name:<10} HTTP {exc.status} - {exc} (trace={exc.trace_id})")
        return False
    except WebIQValidationError as exc:
        print(f"[BAD] {name:<10} {exc}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="microsoft build 2026")
    ap.add_argument("--region", default="US")
    ap.add_argument("--language", default="en")
    ap.add_argument("--browse-url", default="https://news.microsoft.com/source/")
    args = ap.parse_args()

    try:
        client = client_from_env(validate=True)
    except WebIQValidationError as exc:
        print(f"Cannot build client: {exc}")
        print("Set WEBIQ_API_KEY (or WEBIQ_TENANT_ID/CLIENT_ID/CLIENT_SECRET) first.")
        return 2

    q = args.query
    common = dict(region=args.region, language=args.language)
    ok = []

    ok.append(run_case(
        "web", lambda: client.web(q, max_results=5, content_format="passage",
                                  max_length=2000, **common),
        lambda r: f"webResults={len(r.get('webResults', []))}  "
                  f"top: {_first(r.get('webResults'), 'title', 'url')}"))

    ok.append(run_case(
        "videos", lambda: client.videos(q, max_results=5, **common),
        lambda r: f"videoResults={len(r.get('videoResults', []))}  "
                  f"top: {_first(r.get('videoResults'), 'title', 'url')}"))

    ok.append(run_case(
        "browse", lambda: client.browse(args.browse_url, max_length=2000,
                                        content_format="text", **common),
        lambda r: f"title: {str(r.get('title', ''))[:70]}  "
                  f"content_chars={len(str(r.get('content', '')))}"))

    ok.append(run_case(
        "news", lambda: client.news(q, max_results=5, max_length=2000, **common),
        lambda r: f"newsResults={len(r.get('newsResults', []))}  "
                  f"top: {_first(r.get('newsResults'), 'title', 'source')}"))

    ok.append(run_case(
        "images", lambda: client.images(q, max_results=5, **common),
        lambda r: f"imageResults={len(r.get('imageResults', []))}  "
                  f"top: {_first(r.get('imageResults'), 'title', 'url')}"))

    ok.append(run_case(
        "classic", lambda: client.classic(q, max_results_web=3, max_length=1000, **common),
        lambda r: "answers: " + ", ".join(
            k for k in r.data if k.endswith("Results") and r.get(k))))

    print(f"\n----- {sum(ok)}/{len(ok)} endpoints OK -----")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
