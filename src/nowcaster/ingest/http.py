"""Shared HTTP transport with timeouts, retries, rate limiting, and disk cache.

Inputs: URL, method, optional JSON body, query params.
Outputs: parsed JSON (dict | list).
Time allowed to know: wall-clock only for rate limits, retries, and cache TTL;
does not interpret economic observation timestamps.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE_S = 1.0
DEFAULT_MIN_INTERVAL_S = 0.35


class IngestHttpError(RuntimeError):
    """Raised when an upstream HTTP call fails after retries."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitedSession:
    """requests.Session wrapper with polite spacing between calls."""

    def __init__(
        self,
        *,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        user_agent: str = "ca-nowcaster/0.1 (+ingest)",
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_s: float = DEFAULT_BACKOFF_BASE_S,
        cache_dir: Path | None = None,
        cache_enabled: bool | None = None,
    ) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
            }
        )
        self.min_interval_s = min_interval_s
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        self._lock = threading.Lock()
        self._last_request_at = 0.0
        if cache_enabled is None:
            cache_enabled = os.environ.get("NOWCASTER_HTTP_CACHE", "1") not in {
                "0",
                "false",
                "False",
            }
        self.cache_enabled = cache_enabled
        default_cache = Path(os.environ.get("NOWCASTER_CACHE_DIR", "data/cache/http"))
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self.min_interval_s - (now - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def _cache_key(self, method: str, url: str, params: dict | None, body: Any) -> str:
        payload = {
            "method": method.upper(),
            "url": url,
            "params": params or {},
            "body": body,
        }
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> Any | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ignoring corrupt cache file %s: %s", path, exc)
            return None

    def _write_cache(self, key: str, data: Any) -> None:
        path = self._cache_path(key)
        path.write_text(json.dumps(data), encoding="utf-8")

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        use_cache: bool = True,
    ) -> Any:
        """Perform an HTTP request and return JSON.

        Inputs: method, url, optional query params and JSON body.
        Outputs: decoded JSON object.
        Time allowed to know: request/retry clock only; response body timestamps
        are passed through untouched.
        """
        key = self._cache_key(method, url, params, json_body)
        if self.cache_enabled and use_cache:
            cached = self._read_cache(key)
            if cached is not None:
                logger.debug("HTTP cache hit %s %s", method, url)
                return cached

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                response = self._session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                    timeout=self.timeout_s,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                sleep_s = self.backoff_base_s * (2**attempt)
                logger.warning(
                    "HTTP transport error on %s %s (attempt %s/%s): %s; retry in %.1fs",
                    method,
                    url,
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue

            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = IngestHttpError(
                    f"{method} {url} returned {response.status_code}: {response.text[:300]}",
                    status_code=response.status_code,
                )
                if attempt >= self.max_retries:
                    break
                sleep_s = self.backoff_base_s * (2**attempt)
                logger.warning(
                    "HTTP %s from %s; retry in %.1fs",
                    response.status_code,
                    url,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue

            if response.status_code >= 400:
                raise IngestHttpError(
                    f"{method} {url} failed with {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise IngestHttpError(
                    f"{method} {url} returned non-JSON body",
                    status_code=response.status_code,
                ) from exc

            if self.cache_enabled and use_cache:
                self._write_cache(key, data)
            return data

        assert last_error is not None
        raise IngestHttpError(f"{method} {url} failed after retries: {last_error}") from last_error


def cache_key_for_url(url: str, params: dict[str, Any] | None = None) -> str:
    """Stable helper for tests; not used for economic timestamps."""
    qs = urlencode(sorted((params or {}).items()), doseq=True)
    return hashlib.sha256(f"{url}?{qs}".encode()).hexdigest()
