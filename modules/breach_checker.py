"""modules/breach_checker.py — Component 4: breach-exposure checker.

Two complementary, safe lookups:

1. **k-Anonymity range search** (default, no key required)
   The identifier (e-mail or username) is SHA-1 hashed locally and only the
   first 5 hex characters are sent to the HaveIBeenPwned *Pwned Passwords*
   range API (https://api.pwnedpasswords.com/range/XXXXX). The full value
   never leaves the machine. A match means the value appears in HIBP's
   breached-data corpus.

2. **HIBP account lookup** (optional, requires ``HIBP_API_KEY``)
   For e-mails, queries which named breaches contain the account via the
   official v3 API.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from core.engine import ReconEngine
from core.utils import sha1_hex

RANGE_API = "https://api.pwnedpasswords.com/range/{prefix}"
ACCOUNT_API = "https://haveibeenpwned.com/api/v3/breachedaccount/{account}"


async def k_anonymity_lookup(engine: ReconEngine, value: str) -> Dict[str, Any]:
    """Check one value against the HIBP range API using k-anonymity."""
    digest = sha1_hex(value)
    prefix, suffix = digest[:5], digest[5:]

    res = await engine.fetch(RANGE_API.format(prefix=prefix), read_body=True)
    if res.error:
        return {"value": value, "sha1": digest, "exposed": None,
                "error": f"request failed ({res.error})"}
    if res.status != 200:
        return {"value": value, "sha1": digest, "exposed": None,
                "error": f"range API returned HTTP {res.status}"}

    count = 0
    for line in res.body.splitlines():
        line_suffix, _, hits = line.strip().partition(":")
        if line_suffix.upper() == suffix:
            try:
                count = int(hits)
            except ValueError:
                count = 1
            break

    return {
        "value": value,
        "sha1": digest,
        "prefix_sent": prefix,
        "exposed": count > 0,
        "count": count,
    }


async def hibp_account_lookup(
    engine: ReconEngine, email: str, api_key: str
) -> Dict[str, Any]:
    """Official HIBP v3 breach list for an e-mail address (paid key)."""
    res, data = await engine.fetch_json(
        ACCOUNT_API.format(account=email),
        headers={"hibp-api-key": api_key, "Accept": "application/json"},
    )
    if res.error:
        return {"email": email, "error": f"request failed ({res.error})"}
    if res.status == 404:
        return {"email": email, "breaches": [], "found": False}
    if res.status in (401, 403):
        return {"email": email, "error": "HIBP rejected the API key."}
    if res.status == 429:
        return {"email": email, "error": "HIBP rate limit hit. Try again later."}
    if res.status != 200 or not isinstance(data, list):
        return {"email": email, "error": f"unexpected HTTP {res.status} from HIBP"}

    return {
        "email": email,
        "found": True,
        "breaches": [b.get("Name") for b in data if isinstance(b, dict)],
    }


def _candidates(identifier: str) -> List[str]:
    """Normalize an identifier into lookup candidates (deduplicated)."""
    values = [identifier, identifier.lower()]
    seen, out = set(), []
    for v in values:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


async def check_identifier(
    engine: ReconEngine,
    identifier: str,
    kind: str = "auto",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Full breach report for an e-mail or username."""
    api_key = api_key or os.getenv("HIBP_API_KEY", "").strip()
    looks_like_email = "@" in identifier
    if kind == "auto":
        kind = "email" if looks_like_email else "username"

    results = await asyncio.gather(
        *(k_anonymity_lookup(engine, c) for c in _candidates(identifier))
    )

    exposed = any(r.get("exposed") for r in results)
    total = max((r.get("count", 0) for r in results), default=0)
    errors = [r["error"] for r in results if r.get("error")]

    report: Dict[str, Any] = {
        "identifier": identifier,
        "kind": kind,
        "k_anonymity": {
            "exposed": exposed,
            "max_occurrences": total,
            "candidates": results,
        },
        "note": "k-anonymity match = SHA-1 of the value exists in HIBP's breached-data corpus.",
    }

    if errors and not exposed:
        report["errors"] = errors

    # Optional deep check for e-mails when a paid HIBP key is available.
    if kind == "email" and api_key:
        report["account_lookup"] = await hibp_account_lookup(engine, identifier, api_key)

    return report
