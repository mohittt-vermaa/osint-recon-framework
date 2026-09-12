"""modules/game_stats.py — Component 2: public game-stats inspector.

Fetches *public* player data from public APIs:

* Free Fire / Free Fire MAX — looked up by numeric UID through a public
  third-party stats endpoint (Garena shut down the official API).
* PUBG — looked up by in-game name through the official developer API
  (free key: https://developer.pubg.com). Set ``PUBG_API_KEY`` in the
  environment or in a ``.env`` file.

Providers are defined as data, so new titles can be added without touching
callers. Only publicly exposed profile data is retrieved.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from core.engine import ReconEngine

FREEFIRE_PROVIDER = "https://freefire-api.bozvel.com/api/account?id={uid}&lang={lang}"
PUBG_PROVIDER = "https://api.pubg.com/shards/{shard}/players?filter[playerNames]={name}"

SUPPORTED_GAMES = ("freefire", "pubg")


# --------------------------------------------------------------------------
# Free Fire (MAX) — UID based
# --------------------------------------------------------------------------
async def fetch_freefire(
    engine: ReconEngine, uid: str, lang: str = "en"
) -> Dict[str, Any]:
    if not str(uid).isdigit():
        return {"game": "freefire", "found": False,
                "error": "Free Fire lookup requires a numeric UID."}

    url = FREEFIRE_PROVIDER.format(uid=uid, lang=lang)
    res, data = await engine.fetch_json(url, headers={"Accept": "application/json"})

    if res.error:
        return {"game": "freefire", "found": False, "error": f"request failed ({res.error})"}
    if res.status != 200 or not isinstance(data, dict) or not data:
        return {"game": "freefire", "found": False,
                "error": f"provider returned HTTP {res.status or '???'} — UID not found or provider unavailable"}

    # Keep scalar, public profile fields; drop noisy nested blobs.
    profile = {
        k: v for k, v in data.items()
        if isinstance(v, (str, int, float, bool)) and v not in ("", None)
    }
    found = bool(profile.get("nickname"))
    return {
        "game": "Free Fire MAX",
        "provider": "bozvel public stats API",
        "identifier": uid,
        "found": found,
        "data": profile,
    }


# --------------------------------------------------------------------------
# PUBG — official developer API (requires a free API key)
# --------------------------------------------------------------------------
async def fetch_pubg(
    engine: ReconEngine,
    player_name: str,
    shard: str = "steam",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = api_key or os.getenv("PUBG_API_KEY", "").strip()
    if not api_key:
        return {
            "game": "pubg",
            "found": False,
            "error": "PUBG_API_KEY is not set. Get a free key at https://developer.pubg.com "
                     "and put it in your .env file.",
        }

    url = PUBG_PROVIDER.format(shard=shard, name=player_name)
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/vnd.api+json"}
    res, data = await engine.fetch_json(url, headers=headers)

    if res.error:
        return {"game": "pubg", "found": False, "error": f"request failed ({res.error})"}
    if res.status == 401:
        return {"game": "pubg", "found": False, "error": "PUBG API rejected the key (HTTP 401)."}
    if res.status == 429:
        return {"game": "pubg", "found": False, "error": "PUBG API rate limit hit (HTTP 429). Try later."}
    if res.status != 200 or not isinstance(data, dict):
        return {"game": "pubg", "found": False,
                "error": f"unexpected HTTP {res.status} from PUBG API"}

    players = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        players.append({
            "id": item.get("id"),
            "name": attrs.get("name"),
            "patchVersion": attrs.get("patchVersion"),
            "shard": attrs.get("shardId", shard),
        })

    return {
        "game": "PUBG",
        "provider": "official developer.pubg.com API",
        "identifier": player_name,
        "shard": shard,
        "found": bool(players),
        "data": {"players": players},
    }


# --------------------------------------------------------------------------
# Unified dispatcher
# --------------------------------------------------------------------------
async def lookup(
    engine: ReconEngine,
    game: str,
    identifier: str,
    shard: str = "steam",
    lang: str = "en",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    game = (game or "").strip().lower()
    if game in ("freefire", "ff", "ffmax", "freefiremax"):
        return await fetch_freefire(engine, identifier, lang=lang)
    if game == "pubg":
        return await fetch_pubg(engine, identifier, shard=shard, api_key=api_key)
    return {"game": game, "found": False,
            "error": f"Unsupported game '{game}'. Supported: {', '.join(SUPPORTED_GAMES)}"}
