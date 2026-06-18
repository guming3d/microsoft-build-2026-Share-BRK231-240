"""
Microsoft Web IQ (Foundry) v3 REST client.

A thin, dependency-light wrapper around the Web IQ v3 APIs:
    web    -> POST /v3/search/web
    news   -> POST /v3/search/news     (Beta)
    images -> POST /v3/search/images   (Beta)
    videos -> POST /v3/search/videos
    browse -> POST /v3/browse
    classic-> POST /v3/search/classic  (Beta)

Docs: https://webiq.microsoft.ai/documentation/quick-start/

Auth (pick one):
  * API key  -> header  x-apikey: <key>
  * Entra ID -> header  Authorization: Bearer <jwt>
               (client-credentials, scope https://api.microsoft.ai/.default)

The client also encodes the *documented* feature limits so you can test them
both client-side (fast-fail) and server-side (set validate=False).
"""

from __future__ import annotations

import os
import time
import json
import random
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

DEFAULT_BASE_URL = "https://api.microsoft.ai/v3"
ENTRA_SCOPE = "https://api.microsoft.ai/.default"

# --- Documented limits (from the API reference). Used for client-side checks. ---
LIMITS: dict[str, dict[str, Any]] = {
    "query_max_chars": 1000,
    "max_length_max": 500_000,
    "web": {"max_results": 50, "content_formats": {"passage", "text", "html", "markdown"}},
    "news": {"max_results": 20, "content_formats": {"passage", "text", "html", "markdown"}},
    "images": {"max_results": 30},
    "videos": {"max_results": 30},
    "browse": {"content_formats": {"text", "html", "markdown"},
               "live_crawl": {"none", "fallback"}},
    "classic": {"max_results_web": 50, "max_answer_types": 6,
                "content_formats": {"text", "html", "markdown"}},
}

# Status codes that are worth retrying with backoff.
RETRYABLE = {429, 500, 503, 504}


class WebIQError(Exception):
    """Raised for non-success HTTP responses (carries parsed error body)."""

    def __init__(self, status: int, body: Any, trace_id: Optional[str] = None,
                 request_id: Optional[str] = None):
        self.status = status
        self.body = body
        self.trace_id = trace_id
        self.request_id = request_id
        msg = f"HTTP {status}"
        if isinstance(body, dict):
            um = body.get("userMessage") or body.get("errorCode")
            if um:
                msg += f" - {um}"
        super().__init__(msg)


class WebIQValidationError(ValueError):
    """Raised by client-side validation before a request is sent."""


@dataclass
class WebIQResponse:
    """Wraps a successful API response plus timing metadata."""

    status: int
    data: dict[str, Any]
    elapsed_ms: float
    attempts: int = 1
    trace_id: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Parse a duration like '60s' (or a bare number) to seconds."""
    if not value:
        return None
    value = value.strip()
    try:
        if value.endswith("s"):
            return float(value[:-1])
        return float(value)
    except ValueError:
        return None


class EntraTokenProvider:
    """Acquire app-only tokens via MSAL client-credentials. Caches per expiry."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str,
                 scope: str = ENTRA_SCOPE):
        try:
            import msal  # imported lazily so API-key users need no extra deps
        except ImportError as exc:  # pragma: no cover
            raise WebIQValidationError(
                "Entra ID auth requires the 'msal' package. Install with: pip install msal"
            ) from exc
        self._app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        self._scope = scope

    def token(self) -> str:
        result = self._app.acquire_token_for_client(scopes=[self._scope])
        if "access_token" not in result:
            raise WebIQValidationError(
                f"Failed to acquire Entra token: {result.get('error')} "
                f"{result.get('error_description')}"
            )
        return result["access_token"]


class WebIQClient:
    """Synchronous Web IQ v3 client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        token_provider: Optional[EntraTokenProvider] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 4,
        validate: bool = True,
        session: Optional[requests.Session] = None,
    ):
        if not api_key and not token_provider:
            api_key = os.environ.get("WEBIQ_API_KEY")
        if not api_key and not token_provider:
            raise WebIQValidationError(
                "Provide api_key=..., a token_provider=..., or set WEBIQ_API_KEY."
            )
        self.api_key = api_key
        self.token_provider = token_provider
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.validate = validate
        self.session = session or requests.Session()

    # ----------------------------- auth helpers ----------------------------- #
    def _auth_headers(self) -> dict[str, str]:
        if self.token_provider:
            return {"Authorization": f"Bearer {self.token_provider.token()}"}
        return {"x-apikey": self.api_key or ""}

    # --------------------------- core HTTP machinery ------------------------ #
    def _post(self, path: str, body: dict[str, Any]) -> WebIQResponse:
        url = f"{self.base_url}{path}"
        headers = {
            "host": "api.microsoft.ai",
            "content-type": "application/json",
            **self._auth_headers(),
        }
        payload = {k: v for k, v in body.items() if v is not None}

        attempt = 0
        start = time.perf_counter()
        while True:
            attempt += 1
            resp = self.session.post(
                url, headers=headers, data=json.dumps(payload), timeout=self.timeout
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            header_trace = resp.headers.get("traceId") or resp.headers.get("x-trace-id")

            if resp.status_code == 200:
                return WebIQResponse(
                    status=200,
                    data=_safe_json(resp),
                    elapsed_ms=elapsed_ms,
                    attempts=attempt,
                    trace_id=_extract_trace(resp, header_trace),
                    headers=dict(resp.headers),
                )

            # Browse live-crawl in progress -> wait and retry the same request.
            if resp.status_code == 202 and attempt <= self.max_retries:
                wait = _parse_retry_after(_retry_after(resp)) or 2.0
                time.sleep(wait)
                continue

            if resp.status_code in RETRYABLE and attempt <= self.max_retries:
                wait = _parse_retry_after(_retry_after(resp))
                if wait is None:
                    wait = min(2 ** (attempt - 1), 30) + random.uniform(0, 0.5)
                time.sleep(wait)
                continue

            body_parsed = _safe_json(resp)
            raise WebIQError(
                resp.status_code,
                body_parsed,
                trace_id=_extract_trace(resp, header_trace),
                request_id=(body_parsed or {}).get("requestId")
                if isinstance(body_parsed, dict) else None,
            )

    # ------------------------------ validation ------------------------------ #
    def _check_query(self, query: str) -> None:
        if not self.validate:
            return
        if not query or not query.strip():
            raise WebIQValidationError("query is required and cannot be empty.")
        if len(query) > LIMITS["query_max_chars"]:
            raise WebIQValidationError(
                f"query is {len(query)} chars; max is {LIMITS['query_max_chars']}."
            )

    def _check_max_results(self, value: Optional[int], cap: int,
                           name: str = "maxResults") -> None:
        if self.validate and value is not None and not (1 <= value <= cap):
            raise WebIQValidationError(f"{name}={value} out of range (1..{cap}).")

    def _check_max_length(self, value: Optional[int]) -> None:
        if self.validate and value is not None and not (1 <= value <= LIMITS["max_length_max"]):
            raise WebIQValidationError(
                f"maxLength={value} out of range (1..{LIMITS['max_length_max']})."
            )

    def _check_format(self, value: Optional[str], allowed: set[str]) -> None:
        if self.validate and value is not None and value not in allowed:
            raise WebIQValidationError(
                f"contentFormat={value!r} not in {sorted(allowed)}."
            )

    # -------------------------------- endpoints ----------------------------- #
    def web(self, query: str, *, max_results: Optional[int] = None,
            language: Optional[str] = None, region: Optional[str] = None,
            location: Optional[str] = None, content_format: Optional[str] = None,
            max_length: Optional[int] = None) -> WebIQResponse:
        self._check_query(query)
        self._check_max_results(max_results, LIMITS["web"]["max_results"])
        self._check_format(content_format, LIMITS["web"]["content_formats"])
        self._check_max_length(max_length)
        return self._post("/search/web", {
            "query": query, "maxResults": max_results, "language": language,
            "region": region, "location": location, "contentFormat": content_format,
            "maxLength": max_length,
        })

    def news(self, query: str, *, max_results: Optional[int] = None,
             language: Optional[str] = None, region: Optional[str] = None,
             location: Optional[str] = None, content_format: Optional[str] = None,
             max_length: Optional[int] = None) -> WebIQResponse:
        self._check_query(query)
        self._check_max_results(max_results, LIMITS["news"]["max_results"])
        self._check_format(content_format, LIMITS["news"]["content_formats"])
        self._check_max_length(max_length)
        return self._post("/search/news", {
            "query": query, "maxResults": max_results, "language": language,
            "region": region, "location": location, "contentFormat": content_format,
            "maxLength": max_length,
        })

    def images(self, query: str, *, max_results: Optional[int] = None,
               language: Optional[str] = None, region: Optional[str] = None,
               aspect_ratio: Optional[str] = None, color: Optional[str] = None,
               safe_search: Optional[str] = None, image_size: Optional[str] = None,
               watermark_free: Optional[bool] = None, max_height: Optional[int] = None,
               min_height: Optional[int] = None, max_width: Optional[int] = None,
               min_width: Optional[int] = None) -> WebIQResponse:
        self._check_query(query)
        self._check_max_results(max_results, LIMITS["images"]["max_results"])
        return self._post("/search/images", {
            "query": query, "maxResults": max_results, "language": language,
            "region": region, "aspectRatio": aspect_ratio, "color": color,
            "safeSearch": safe_search, "imageSize": image_size,
            "watermarkFree": watermark_free, "maxHeight": max_height,
            "minHeight": min_height, "maxWidth": max_width, "minWidth": min_width,
        })

    def videos(self, query: str, *, max_results: Optional[int] = None,
               language: Optional[str] = None, region: Optional[str] = None,
               enable_playlist: Optional[bool] = None, freshness: Optional[str] = None,
               embeddable: Optional[list[str]] = None, resolution: Optional[str] = None,
               safe_search: Optional[str] = None, duration: Optional[str] = None) -> WebIQResponse:
        self._check_query(query)
        self._check_max_results(max_results, LIMITS["videos"]["max_results"])
        return self._post("/search/videos", {
            "query": query, "maxResults": max_results, "language": language,
            "region": region, "enablePlaylist": enable_playlist, "freshness": freshness,
            "embeddable": embeddable, "resolution": resolution,
            "safeSearch": safe_search, "duration": duration,
        })

    def browse(self, url: str, *, max_length: Optional[int] = None,
               live_crawl: Optional[str] = None, include_web_links: Optional[bool] = None,
               render_dynamic_pages: Optional[bool] = None,
               include_image_links: Optional[bool] = None, language: Optional[str] = None,
               region: Optional[str] = None, content_format: Optional[str] = None) -> WebIQResponse:
        if self.validate:
            if not url:
                raise WebIQValidationError("url is required.")
            if live_crawl is not None and live_crawl not in LIMITS["browse"]["live_crawl"]:
                raise WebIQValidationError(
                    f"liveCrawl={live_crawl!r} not in {sorted(LIMITS['browse']['live_crawl'])}."
                )
            if render_dynamic_pages and live_crawl != "fallback":
                raise WebIQValidationError(
                    "renderDynamicPages only works when liveCrawl='fallback'."
                )
        self._check_max_length(max_length)
        self._check_format(content_format, LIMITS["browse"]["content_formats"])
        return self._post("/browse", {
            "url": url, "maxLength": max_length, "liveCrawl": live_crawl,
            "includeWebLinks": include_web_links, "renderDynamicPages": render_dynamic_pages,
            "includeImageLinks": include_image_links, "language": language,
            "region": region, "contentFormat": content_format,
        })

    def classic(self, query: str, *, max_answer_types: Optional[int] = None,
                region: Optional[str] = None, language: Optional[str] = None,
                location: Optional[str] = None, max_results_web: Optional[int] = None,
                max_length: Optional[int] = None, content_format: Optional[str] = None,
                freshness: Optional[str] = None, response_filter: Optional[list[str]] = None,
                safe_search: Optional[str] = None) -> WebIQResponse:
        self._check_query(query)
        self._check_max_results(max_results_web, LIMITS["classic"]["max_results_web"],
                                name="maxResultsWeb")
        self._check_max_length(max_length)
        self._check_format(content_format, LIMITS["classic"]["content_formats"])
        if self.validate and max_answer_types is not None and not (
                1 <= max_answer_types <= LIMITS["classic"]["max_answer_types"]):
            raise WebIQValidationError(
                f"maxAnswerTypes={max_answer_types} out of range "
                f"(1..{LIMITS['classic']['max_answer_types']})."
            )
        return self._post("/search/classic", {
            "query": query, "maxAnswerTypes": max_answer_types, "region": region,
            "language": language, "location": location, "maxResultsWeb": max_results_web,
            "maxLength": max_length, "contentFormat": content_format,
            "freshness": freshness, "responseFilter": response_filter,
            "safeSearch": safe_search,
        })


# ------------------------------- module helpers ----------------------------- #
def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError):
        return {"_raw": resp.text[:2000]}


def _retry_after(resp: requests.Response) -> Optional[str]:
    body = _safe_json(resp)
    if isinstance(body, dict) and body.get("retryAfter"):
        return body["retryAfter"]
    return resp.headers.get("Retry-After")


def _extract_trace(resp: requests.Response, header_trace: Optional[str]) -> Optional[str]:
    if header_trace:
        return header_trace
    body = _safe_json(resp)
    if isinstance(body, dict):
        return body.get("traceId")
    return None


def client_from_env(validate: bool = True) -> WebIQClient:
    """Build a client from environment variables.

    API key:    WEBIQ_API_KEY
    Entra ID:   WEBIQ_TENANT_ID, WEBIQ_CLIENT_ID, WEBIQ_CLIENT_SECRET
    Base URL:   WEBIQ_BASE_URL (optional)
    """
    base_url = os.environ.get("WEBIQ_BASE_URL", DEFAULT_BASE_URL)
    tenant = os.environ.get("WEBIQ_TENANT_ID")
    client_id = os.environ.get("WEBIQ_CLIENT_ID")
    secret = os.environ.get("WEBIQ_CLIENT_SECRET")
    if tenant and client_id and secret:
        provider = EntraTokenProvider(tenant, client_id, secret)
        return WebIQClient(token_provider=provider, base_url=base_url, validate=validate)
    return WebIQClient(api_key=os.environ.get("WEBIQ_API_KEY"),
                       base_url=base_url, validate=validate)
