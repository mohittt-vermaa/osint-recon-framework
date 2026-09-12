"""core/engine.py — the asynchronous network engine that powers every module.

Features
--------
* single pooled ``aiohttp.ClientSession`` (connection reuse, DNS cache)
* randomized User-Agent rotation on every request
* strict connect / total timeouts
* bounded concurrency through an ``asyncio.Semaphore``
* automatic retries with jittered backoff for transport-level failures
* graceful classification of blocked endpoints (401/403/429/451/503)

Every method is non-blocking; callers ``await`` results.
"""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

#: Rotating pool of current desktop browser User-Agents (Windows + Linux).
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.65",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

#: HTTP codes that usually mean the target actively rejected the probe.
BLOCKED_STATUS_CODES = {401, 403, 429, 451, 503}

#: Status codes worth retrying once (transient server-side hiccups).
RETRY_STATUS_CODES = {500, 502, 504}


@dataclass
class ProbeResult:
    """Outcome of a single HTTP probe."""

    url: str
    status: int = 0
    blocked: bool = False
    error: Optional[str] = None
    elapsed_ms: int = 0
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.status) and not self.error and not self.blocked


class ReconEngine:
    """Async context manager wrapping a pooled, throttled HTTP session.

    Example
    -------
    async with ReconEngine(max_concurrency=25, total_timeout=12) as engine:
        res = await engine.fetch("https://github.com/octocat")
    """

    def __init__(
        self,
        max_concurrency: int = 20,
        total_timeout: float = 15.0,
        connect_timeout: float = 8.0,
        retries: int = 2,
        user_agents: Optional[List[str]] = None,
    ) -> None:
        self.max_concurrency = max_concurrency
        self.total_timeout = total_timeout
        self.connect_timeout = connect_timeout
        self.retries = retries
        self.user_agents = list(user_agents) if user_agents else list(USER_AGENTS)
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    # -- lifecycle ---------------------------------------------------------
    async def __aenter__(self) -> "ReconEngine":
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrency,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(
                total=self.total_timeout, connect=self.connect_timeout
            ),
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
        self._semaphore = None

    def _random_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        if extra:
            headers.update(extra)
        return headers

    # -- public API ----------------------------------------------------------
    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        read_body: bool = True,
        allow_redirects: bool = True,
    ) -> ProbeResult:
        """Perform one resilient HTTP request. Never raises for network errors."""
        if self._session is None or self._semaphore is None:
            raise RuntimeError("ReconEngine must be used inside `async with`.")

        merged_headers = self._random_headers(headers)
        last_error: Optional[str] = None

        for attempt in range(self.retries + 1):
            assert self._semaphore is not None
            async with self._semaphore:
                start = time.perf_counter()
                try:
                    async with self._session.request(
                        method,
                        url,
                        headers=merged_headers,
                        allow_redirects=allow_redirects,
                    ) as resp:
                        body = await resp.text(errors="replace") if read_body else ""
                        elapsed = int((time.perf_counter() - start) * 1000)
                        status = resp.status

                        # transient server errors → retry
                        if status in RETRY_STATUS_CODES and attempt < self.retries:
                            last_error = f"HTTP {status}"
                            await self._backoff(attempt)
                            continue

                        return ProbeResult(
                            url=url,
                            status=status,
                            blocked=status in BLOCKED_STATUS_CODES,
                            error=None,
                            elapsed_ms=elapsed,
                            body=body,
                            headers=dict(resp.headers),
                        )
                except asyncio.TimeoutError:
                    last_error = "timeout"
                except aiohttp.ClientError as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                except Exception as exc:  # noqa: BLE001 — never crash a scan
                    last_error = f"Unexpected: {type(exc).__name__}: {exc}"

            if attempt < self.retries:
                await self._backoff(attempt)

        return ProbeResult(url=url, error=last_error or "unknown error")

    async def fetch_json(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
    ) -> tuple[ProbeResult, Optional[Any]]:
        """Fetch a URL and best-effort parse the body as JSON."""
        res = await self.fetch(url, method=method, headers=headers, read_body=True)
        if res.error or not res.body:
            return res, None
        import json

        try:
            return res, json.loads(res.body)
        except (json.JSONDecodeError, ValueError):
            return res, None

    @staticmethod
    async def _backoff(attempt: int) -> None:
        await asyncio.sleep(0.4 * (attempt + 1) + random.uniform(0.0, 0.3))
