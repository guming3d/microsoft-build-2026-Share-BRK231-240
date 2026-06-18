# Web IQ (Foundry) v3 — Test Client

A small Python client and test harness for **Microsoft Web IQ** — the AI-native
grounding APIs documented at
<https://webiq.microsoft.ai/documentation/quick-start/>.

It lets you:

- call every v3 endpoint (`web`, `news`, `images`, `videos`, `browse`, `classic`),
- **test the documented feature limits** both client-side and server-side,
- **benchmark performance** (latency p50/p90/p95/p99) against the documented
  **164 ms p95** target, and probe rate-limit (429) behaviour under concurrency.

> Web IQ is in **limited access**. You need an API key or an Entra ID app
> registration bound in the [portal](https://webiq.microsoft.ai/profiles).

---

## What the docs say (limits captured in this client)

**Base URL:** `https://api.microsoft.ai/v3` &nbsp;•&nbsp; **HTTPS only** (HTTP → `410`).

### Endpoints & feature limits

| Endpoint  | Path                  | Status | `maxResults` (default → max) | Notes |
|-----------|-----------------------|--------|------------------------------|-------|
| Web       | `POST /search/web`    | GA     | 10 → **50**                  | `contentFormat`: `passage`/`text`/`html`/`markdown`. No `snippet` field — use `passage`. |
| Videos    | `POST /search/videos` | GA     | 30 → **30**                  | `freshness`, `duration`, `resolution`, `embeddable`, `enablePlaylist`. |
| Browse    | `POST /browse`        | GA     | n/a                          | `contentFormat`: `text`/`html`/`markdown` only. `liveCrawl`: `none`/`fallback`. `renderDynamicPages` needs `liveCrawl=fallback`. `202`+`retryAfter` while crawling; `430` if too many on-demand crawls. |
| News      | `POST /search/news`   | **Beta** | 10 → **20**                | Retains `snippet`. May return fewer results during Beta. |
| Images    | `POST /search/images` | **Beta** | 30 → **30**                | Size/colour/aspect/watermark filters. |
| Classic   | `POST /search/classic`| **Beta** | web 10 → **50**            | Aggregated multi-answer (web/image/video/news/entity/finance/sports/…). `maxAnswerTypes` ≤ 6. |

Common limits: **`query` ≤ 1000 chars**, **`maxLength` ≤ 500000 chars** (default 10000),
`language` = ISO 639-1, `region` = 2-letter code, `location` = `lat:..;long:..`.

### Performance & operational limits

- **Latency:** documented **164 ms p95** (≈2.5× faster than the prior best alternative).
- **Rate limiting:** `429 Too Many Requests` with a `retryAfter` field (e.g. `"60s"`).
  No fixed public RPS/QPS is published — contact support for higher limits.
- **Retry guidance:** exponential backoff on `429`/`500`/`503`; for Browse,
  handle `202` by waiting `retryAfter` and retrying the same request.
- **Coverage caveats:** `crawledAt` / `lastUpdatedAt` / `thumbnail` / video `moments`
  are best-effort and may be empty. Beta endpoints aren't production-ready.
- **MCP:** the MCP server (`https://api.microsoft.ai/v3/mcp`) only exposes the
  tools your key/Entra app is entitled to.

---

## Setup

```bash
cd webiq-test-client
python -m venv .venv && . .venv/Scripts/activate    # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env        # then edit .env
# Or just set the env var directly:
#   PowerShell:  $env:WEBIQ_API_KEY = "<your key>"
#   bash:        export WEBIQ_API_KEY="<your key>"
```

Auth resolves automatically:

- If `WEBIQ_TENANT_ID` + `WEBIQ_CLIENT_ID` + `WEBIQ_CLIENT_SECRET` are set →
  **Entra ID** (OAuth client-credentials, scope `https://api.microsoft.ai/.default`).
- Else `WEBIQ_API_KEY` → **API key** (`x-apikey` header).

> Never commit `.env` or hard-code keys.

---

## Usage

### 1. Limit tests

```bash
# Client-side validation only — no network, no key needed:
python test_limits.py --offline

# Also verify the *server* enforces the limits (needs a key):
python test_limits.py
```

### 2. Smoke test (one call per endpoint)

```bash
python smoke_test.py --query "microsoft build 2026"
```

### 3. Performance benchmark

```bash
python benchmark.py --endpoint web -n 50                 # latency percentiles vs 164ms p95
python benchmark.py --endpoint web -n 100 --concurrency 8 # probe throughput / 429s
python benchmark.py --endpoint browse --url https://news.microsoft.com/source/
```

### 4. Library use

```python
from webiq_client import client_from_env

client = client_from_env()                      # reads env vars
r = client.web("latest trends in LLM RAG",
               max_results=10, content_format="passage", max_length=2000)
print(r.elapsed_ms, "ms", "trace:", r.trace_id)
for hit in r["webResults"]:
    print(hit["title"], hit["url"])
```

The client validates inputs against the documented limits **before** sending
(raising `WebIQValidationError`). Pass `validate=False` to bypass that and test
the server's own enforcement. Transient errors (`429/500/503/504`) and Browse
`202` are retried with backoff that honours `retryAfter`.

---

## Feature investigation (critical user questions)

Targeted tests that answer real adoption questions, each reproducible:

```bash
python verify_consistency.py             # are repeat calls stable? (yes, 100%)
python test_q1_freshness.py              # cache TTL, news freshness filter, cache-bust
python test_q1_freshness.py --skip-ttl   # skip the slow 5-min TTL probe
python test_q2_pagination.py             # is there pagination beyond maxResults?
python test_q4_coldstart.py              # cold-start vs warm latency penalty
python test_q7_browse.py                 # robots.txt, paywalls, JS rendering
python test_q7_browse.py --burst 15      # probe the 430 "too many crawls" ceiling
```

Key findings (verified live, 2026-06-18):

| Question | Finding |
|----------|---------|
| Determinism | Same query returns **identical** results every call (100% overlap). |
| Cache TTL | Result set stable for the full 5-min window (**TTL >= 300s**). |
| `news` freshness | **No-op** - day/week/month/year all return the same set. |
| Pagination | **None.** `maxResults` is a hard ceiling; 8 paging params ignored. |
| Ranking | `web` re-orders by size (top-10 not a prefix of top-50); `news` is prefix-stable. |
| Cold-start | **7-15x** penalty: cold 1.2-1.7s vs warm 0.1-0.2s. Reuse a keep-alive session. |
| Browse robots | Enforced - LinkedIn/Facebook return **HTTP 403** (dropped). |
| Browse JS render | Only on live crawl; uncached pages return **202** then ~4.6s. |

Non-testable questions (SLA, regional endpoints, crawl/content licensing,
attribution, GDPR/data-residency) are summarized for vendor follow-up in
**`WebIQ_Findings_and_Open_Questions.pptx`** (regenerate with
`python make_findings_ppt.py`).

---

## Files

| File              | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| `webiq_client.py` | Client library: auth, all endpoints, validation, retry/backoff |
| `test_limits.py`  | Feature-limit tests (offline client-side + online server-side) |
| `smoke_test.py`   | One call per endpoint; prints status, latency, trace, sample   |
| `benchmark.py`    | Latency percentiles + concurrency/rate-limit probing           |
| `verify_consistency.py` | Repeat-call result stability check                       |
| `test_q1_freshness.py`  | Q1: cache TTL, `news` freshness filter, cache-bust probe |
| `test_q2_pagination.py` | Q2: subset/prefix check + pagination param probe         |
| `test_q4_coldstart.py`  | Q4: cold-start vs warm latency per endpoint              |
| `test_q7_browse.py`     | Q7: robots.txt, paywall, JS-render, crawl-limit burst    |
| `make_findings_ppt.py`  | Generates the findings + open-questions slide deck       |
| `WebIQ_Findings_and_Open_Questions.pptx` | 11-slide summary for vendor review      |
| `requirements.txt`| `requests` (+ optional `msal` for Entra); `python-pptx` for the deck |
| `.env.example`    | Credential template                                            |

Support: WebIQ-Support@microsoft.com
