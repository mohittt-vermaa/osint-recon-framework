"""modules/metadata_extractor.py — Component 3: public metadata extractor.

Scrapes Open Graph / Twitter Card / standard meta tags from any public page
(profiles, posts, sites) using BeautifulSoup4. No authentication, no login —
only data the server chooses to publish is read.
"""
from __future__ import annotations

from typing import Any, Dict, List

from bs4 import BeautifulSoup

from core.engine import ReconEngine

OG_PROPERTIES = [
    "og:title", "og:description", "og:image", "og:url",
    "og:type", "og:site_name", "og:locale",
]
TWITTER_PROPERTIES = ["twitter:title", "twitter:description", "twitter:image", "twitter:card"]


async def extract(engine: ReconEngine, url: str) -> Dict[str, Any]:
    res = await engine.fetch(url, read_body=True)

    if res.error:
        return {"url": url, "found": False, "error": f"request failed ({res.error})"}
    if res.blocked:
        return {"url": url, "found": False,
                "error": f"blocked by the server (HTTP {res.status}) — nothing to extract"}
    if res.status >= 400:
        return {"url": url, "found": False, "error": f"HTTP {res.status}"}

    soup = BeautifulSoup(res.body, "html.parser")
    metadata: Dict[str, str] = {}

    # Open Graph + Twitter Card tags (meta[property=...])
    for prop in OG_PROPERTIES + TWITTER_PROPERTIES:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            metadata[prop] = tag["content"].strip()

    # Classic meta tags (meta[name=...])
    for name in ("description", "keywords", "author"):
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            metadata[name] = tag["content"].strip()

    # Page title
    title = soup.title.get_text(strip=True) if soup.title else None

    # Canonical URL
    canonical = None
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        canonical = link["href"]

    # Any og:image alternatives served via rel=image_src
    if "og:image" not in metadata:
        img_link = soup.find("link", rel="image_src")
        if img_link and img_link.get("href"):
            metadata["og:image"] = img_link["href"]

    found = bool(metadata or title)
    return {
        "url": url,
        "found": found,
        "status": res.status,
        "title": title,
        "canonical": canonical,
        "metadata": metadata,
        "elapsed_ms": res.elapsed_ms,
    }
