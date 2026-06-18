"""
Q7 - Browse-specific behavior.

Answers (via live calls to /browse):
  A. robots.txt     - does browse fetch a page that commonly disallows crawlers?
  B. paywall        - what comes back for a known paywalled article (full text,
                      partial, or just the metered preview)?
  C. JS rendering   - latency + content-size delta of renderDynamicPages=True
                      (liveCrawl='fallback') vs a plain static fetch, on a JS-heavy SPA.
  D. crawl limit    - (optional, --burst) fire many liveCrawl='fallback' requests to try
                      to trigger the documented 430 "too many crawls".

Usage:
  python test_q7_browse.py
  python test_q7_browse.py --burst 15
"""
from __future__ import annotations
import argparse
from webiq_client import client_from_env, WebIQError


def content_of(data: dict) -> str:
    for k in ("content", "text", "markdown", "html"):
        v = data.get(k)
        if isinstance(v, str) and v:
            return v
    page = data.get("page") or data.get("result") or {}
    if isinstance(page, dict):
        for k in ("content", "text", "markdown", "html"):
            v = page.get(k)
            if isinstance(v, str) and v:
                return v
    return ""


def show(label: str, resp) -> str:
    body = content_of(resp.data)
    title = resp.data.get("title") or resp.data.get("pageTitle") or "(no title)"
    print(f"  {label}: HTTP {resp.status}  {resp.elapsed_ms:.0f} ms  "
          f"title={title[:50]!r}  content_chars={len(body)}")
    return body


def test_robots(client) -> None:
    print("\n" + "=" * 70)
    print("A. robots.txt-restricted target")
    print("=" * 70)
    targets = ["https://www.linkedin.com/feed/", "https://www.facebook.com/"]
    for url in targets:
        try:
            r = client.browse(url, live_crawl="fallback")
            body = show(url, r)
            note = "got content (robots.txt NOT enforced)" if len(body) > 200 \
                else "little/no content (possibly blocked or login-walled)"
            print(f"        -> {note}")
        except WebIQError as exc:
            print(f"  {url}: HTTP {exc.status}  {exc}")


def test_paywall(client) -> None:
    print("\n" + "=" * 70)
    print("B. paywalled article")
    print("=" * 70)
    targets = [
        "https://www.wsj.com/tech",
        "https://www.nytimes.com/section/technology",
    ]
    for url in targets:
        try:
            r = client.browse(url, live_crawl="fallback")
            body = show(url, r)
            lc = body.lower()
            metered = any(w in lc for w in ("subscribe", "subscription", "sign in", "paywall"))
            print(f"        -> {'paywall/subscribe markers present' if metered else 'no obvious paywall markers'}")
        except WebIQError as exc:
            print(f"  {url}: HTTP {exc.status}  {exc}")


def test_js_render(client) -> None:
    print("\n" + "=" * 70)
    print("C. JS rendering: renderDynamicPages on vs off")
    print("=" * 70)
    url = "https://react.dev/"
    try:
        static = client.browse(url, live_crawl="fallback")
        static_body = show("static  (no JS)  ", static)
    except WebIQError as exc:
        print(f"  static: HTTP {exc.status}  {exc}")
        return
    try:
        rendered = client.browse(url, live_crawl="fallback", render_dynamic_pages=True)
        rendered_body = show("rendered (JS on) ", rendered)
    except WebIQError as exc:
        print(f"  rendered: HTTP {exc.status}  {exc}")
        return

    dlat = rendered.elapsed_ms - static.elapsed_ms
    dlen = len(rendered_body) - len(static_body)
    print(f"\n  latency delta (JS on - off): {dlat:+.0f} ms")
    print(f"  content delta (JS on - off): {dlen:+d} chars")
    print("\n  --- verdict ---")
    if dlen > 200:
        print("  JS rendering returns MORE content -> matters for SPA/dynamic pages.")
    else:
        print("  Little content difference here (page may be SSR'd already).")
    print(f"  Rendering cost ~{dlat:+.0f} ms extra latency.")


def test_burst(client, n: int) -> None:
    print("\n" + "=" * 70)
    print(f"D. crawl-limit burst: {n} live-crawl requests (looking for HTTP 430)")
    print("=" * 70)
    codes: dict[str, int] = {}
    for i in range(n):
        try:
            r = client.browse(f"https://example.com/?probe={i}", live_crawl="fallback")
            codes[str(r.status)] = codes.get(str(r.status), 0) + 1
        except WebIQError as exc:
            key = str(exc.status)
            codes[key] = codes.get(key, 0) + 1
            if exc.status == 430:
                print(f"  request {i+1}: HTTP 430 TOO MANY CRAWLS (retryAfter={getattr(exc,'retry_after',None)})")
    print(f"  status distribution: {codes}")
    print("  --- verdict ---")
    if "430" in codes:
        print("  Hit the 430 crawl ceiling -> live crawls are rate-limited separately.")
    else:
        print(f"  No 430 across {n} crawls -> ceiling is higher than {n} (or per longer window).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--burst", type=int, default=0, help="if >0, run N-request crawl burst")
    args = ap.parse_args()
    client = client_from_env()
    test_robots(client)
    test_paywall(client)
    test_js_render(client)
    if args.burst > 0:
        test_burst(client, args.burst)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
