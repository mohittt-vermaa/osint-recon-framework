"""modules/username_recon.py — Component 1: cross-platform username recon.

Verifies whether a username exists on social / gaming networks by probing
public profile URLs and classifying the HTTP response. Platform definitions
live in ``config/platforms.json`` (fully configurable, no code changes needed).
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.engine import ReconEngine
from core.utils import DEFAULT_PLATFORMS_FILE, load_json

# Verdict constants
FOUND = "FOUND"
NOT_FOUND = "NOT_FOUND"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"
ERROR = "ERROR"

ProgressCB = Optional[Callable[["PlatformResult"], Awaitable[None]]]


@dataclass
class PlatformResult:
    platform: str
    category: str
    url: str
    status: int
    state: str
    elapsed_ms: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_platforms(path: Any = DEFAULT_PLATFORMS_FILE) -> List[Dict[str, Any]]:
    """Load platform definitions and merge per-entry defaults."""
    raw = load_json(path)
    defaults = raw.get("defaults", {})
    default_match = defaults.get("match", {})
    platforms: List[Dict[str, Any]] = []
    for entry in raw.get("platforms", []):
        merged = dict(defaults)
        merged.update(entry)
        match = dict(default_match)
        match.update(entry.get("match", {}))
        merged["match"] = match
        platforms.append(merged)
    return platforms


def _classify(probe, match: Dict[str, Any]) -> str:
    """Turn a ProbeResult into a verdict using the platform's match rules."""
    if probe.error:
        return ERROR
    if probe.blocked:
        return BLOCKED

    body = probe.body.lower()
    for needle in match.get("body_contains", []):
        if needle.lower() not in body:
            return NOT_FOUND
    for needle in match.get("body_not_contains", []):
        if needle.lower() in body:
            return NOT_FOUND

    if probe.status in match.get("found_status", [200]):
        return FOUND
    if probe.status in match.get("not_found_status", [404]):
        return NOT_FOUND
    return UNKNOWN


async def probe_platform(
    engine: ReconEngine, platform: Dict[str, Any], username: str
) -> PlatformResult:
    url = platform["url"].format(username=username)
    probe = await engine.fetch(
        url,
        method=platform.get("method", "GET"),
        headers=platform.get("headers"),
        read_body=bool(platform["match"].get("body_contains")
                        or platform["match"].get("body_not_contains")),
    )
    return PlatformResult(
        platform=platform["name"],
        category=platform.get("category", "general"),
        url=url,
        status=probe.status,
        state=_classify(probe, platform["match"]),
        elapsed_ms=probe.elapsed_ms,
        error=probe.error,
    )


_STATE_ORDER = {FOUND: 0, UNKNOWN: 1, BLOCKED: 2, NOT_FOUND: 3, ERROR: 4}


async def scan(
    engine: ReconEngine,
    username: str,
    platforms: Optional[List[Dict[str, Any]]] = None,
    progress_cb: ProgressCB = None,
) -> List[PlatformResult]:
    """Probe every platform concurrently and return sorted verdicts."""
    platforms = platforms if platforms is not None else load_platforms()

    async def _worker(p: Dict[str, Any]) -> PlatformResult:
        result = await probe_platform(engine, p, username)
        if progress_cb is not None:
            await progress_cb(result)
        return result

    results = await asyncio.gather(*(_worker(p) for p in platforms))
    return sorted(results, key=lambda r: (_STATE_ORDER.get(r.state, 9), r.platform.lower()))


def summarize(results: List[PlatformResult]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for r in results:
        summary[r.state] = summary.get(r.state, 0) + 1
    return summary
