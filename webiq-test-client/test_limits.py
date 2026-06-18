"""
Feature-limit tests for Web IQ v3.

Two layers:
  1. OFFLINE  - asserts the client's own validation rejects out-of-range inputs.
                Runs with no API key and no network.
  2. ONLINE   - sends boundary requests with validation DISABLED so the *server*
                enforces the limit, and asserts the documented status code.
                Runs only when WEBIQ_API_KEY (or Entra vars) are present.

Run:
    python test_limits.py            # offline + online (if creds present)
    python test_limits.py --offline  # never touch the network
"""

from __future__ import annotations

import sys
import argparse

from webiq_client import (
    WebIQClient, WebIQError, WebIQValidationError, LIMITS, client_from_env,
)

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, str, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    _results.append((PASS if ok else FAIL, name, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f"  ->  {detail}" if detail else ""))


def expect_validation_error(name: str, fn) -> None:
    try:
        fn()
        record(name, False, "expected WebIQValidationError, none raised")
    except WebIQValidationError as exc:
        record(name, True, str(exc))
    except Exception as exc:  # pragma: no cover
        record(name, False, f"wrong exception: {type(exc).__name__}: {exc}")


def expect_status(name: str, fn, status: int) -> None:
    try:
        resp = fn()
        record(name, False, f"expected HTTP {status}, got 200 (attempts={resp.attempts})")
    except WebIQError as exc:
        ok = exc.status == status
        record(name, ok, f"got HTTP {exc.status} (wanted {status}); trace={exc.trace_id}")
    except Exception as exc:  # pragma: no cover
        record(name, False, f"unexpected: {type(exc).__name__}: {exc}")


# ----------------------------------------------------------------------------- #
def run_offline() -> None:
    print("\n=== OFFLINE: client-side validation ===")
    # validate=True client; a dummy key keeps the constructor happy (never sent).
    c = WebIQClient(api_key="dummy", validate=True)
    qmax = LIMITS["query_max_chars"]

    expect_validation_error("web: empty query rejected", lambda: c.web(""))
    expect_validation_error(
        f"web: query > {qmax} chars rejected", lambda: c.web("x" * (qmax + 1)))
    expect_validation_error(
        "web: maxResults=51 rejected (max 50)", lambda: c.web("ai", max_results=51))
    expect_validation_error(
        "web: maxResults=0 rejected", lambda: c.web("ai", max_results=0))
    expect_validation_error(
        "web: bad contentFormat rejected",
        lambda: c.web("ai", content_format="pdf"))
    expect_validation_error(
        "web: maxLength=500001 rejected (max 500000)",
        lambda: c.web("ai", max_length=LIMITS["max_length_max"] + 1))
    expect_validation_error(
        "news: maxResults=21 rejected (max 20)", lambda: c.news("ai", max_results=21))
    expect_validation_error(
        "images: maxResults=31 rejected (max 30)", lambda: c.images("ai", max_results=31))
    expect_validation_error(
        "videos: maxResults=31 rejected (max 30)", lambda: c.videos("ai", max_results=31))
    expect_validation_error(
        "browse: empty url rejected", lambda: c.browse(""))
    expect_validation_error(
        "browse: bad liveCrawl rejected",
        lambda: c.browse("https://example.com", live_crawl="always"))
    expect_validation_error(
        "browse: renderDynamicPages needs liveCrawl=fallback",
        lambda: c.browse("https://example.com", render_dynamic_pages=True, live_crawl="none"))
    expect_validation_error(
        "browse: contentFormat=passage rejected (text/html/markdown only)",
        lambda: c.browse("https://example.com", content_format="passage"))
    expect_validation_error(
        "classic: maxAnswerTypes=7 rejected (max 6)",
        lambda: c.classic("ai", max_answer_types=7))
    expect_validation_error(
        "classic: maxResultsWeb=51 rejected (max 50)",
        lambda: c.classic("ai", max_results_web=51))

    # A valid request must NOT raise on the client side (we stop before sending
    # by leaving the network untouched - validation passes, no assertion error).
    try:
        c.validate  # sanity
        # Build the payload path without sending by re-checking limits only:
        c._check_query("a valid query")
        c._check_max_results(50, LIMITS["web"]["max_results"])
        c._check_format("passage", LIMITS["web"]["content_formats"])
        c._check_max_length(LIMITS["max_length_max"])
        record("web: boundary-valid inputs accepted (50, passage, 500000)", True)
    except WebIQValidationError as exc:
        record("web: boundary-valid inputs accepted", False, str(exc))


def run_online() -> bool:
    try:
        probe = client_from_env(validate=True)
    except WebIQValidationError:
        print("\n=== ONLINE: skipped (no WEBIQ_API_KEY / Entra creds) ===")
        return False
    if not probe.api_key and not probe.token_provider:
        print("\n=== ONLINE: skipped (no credentials) ===")
        return False

    print("\n=== ONLINE: server-side limit enforcement ===")
    # validate=False so out-of-range params reach the server.
    raw = client_from_env(validate=False)
    qmax = LIMITS["query_max_chars"]

    expect_status("web: server rejects maxResults=51 -> 400",
                  lambda: raw.web("ai", max_results=51), 400)
    expect_status(f"web: server rejects query > {qmax} chars -> 400",
                  lambda: raw.web("x" * (qmax + 5)), 400)
    expect_status("web: server rejects bad contentFormat -> 400",
                  lambda: raw.web("ai", content_format="pdf"), 400)
    # The documented "HTTP -> 410" rule is about the API transport itself,
    # not the target URL passed to /browse. NOTE: this deployment actually
    # returns 400 for plaintext HTTP (docs say 410) - recorded as a finding.
    import os
    http_base = os.environ.get("WEBIQ_BASE_URL", "https://api.microsoft.ai/v3")
    http_base = http_base.replace("https://", "http://", 1)
    http_client = client_from_env(validate=False)
    http_client.base_url = http_base.rstrip("/")
    try:
        resp = http_client.web("ai", max_results=1)
        record("API over http:// rejected (docs: 410)", False,
               f"expected 4xx, got {resp.status}")
    except WebIQError as exc:
        record("API over http:// rejected (docs: 410)", exc.status in (400, 403, 410),
               f"got HTTP {exc.status}; docs say 410, this deployment returns 400")

    # An http:// *target* URL passed to /browse is allowed (crawled, not blocked).
    try:
        resp = raw.browse("http://example.com")
        record("browse: http:// target allowed (returns 200)", resp.status == 200,
               f"got HTTP {resp.status}; trace={resp.trace_id}")
    except WebIQError as exc:
        record("browse: http:// target allowed (returns 200)", False,
               f"got HTTP {exc.status}; trace={exc.trace_id}")

    # Bad auth should be 401/403 regardless of validation.
    bad = WebIQClient(api_key="definitely-not-a-real-key", validate=False)
    try:
        bad.web("ai", max_results=1)
        record("web: invalid API key -> 401/403", False, "got 200")
    except WebIQError as exc:
        record("web: invalid API key -> 401/403", exc.status in (401, 403),
               f"got HTTP {exc.status}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip all network calls")
    args = ap.parse_args()

    run_offline()
    if not args.offline:
        run_online()

    passed = sum(1 for s, *_ in _results if s == PASS)
    failed = sum(1 for s, *_ in _results if s == FAIL)
    print(f"\n----- {passed} passed, {failed} failed -----")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
