"""core/utils.py — shared helpers (paths, JSON, hashing, formatting)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

#: Repository root (the folder that contains main.py).
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PLATFORMS_FILE = REPO_ROOT / "config" / "platforms.json"
RESULTS_DIR = REPO_ROOT / "results"


def load_json(path: Path | str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path | str, data: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return path


def sha1_hex(value: str) -> str:
    """Uppercase SHA-1 hex digest (HIBP k-anonymity uses uppercase)."""
    return hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest().upper()


def chunk_text(text: str, size: int = 4000) -> List[str]:
    """Split long text into chunks that fit Telegram's 4096-char limit."""
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def print_kv(data: Dict[str, Any], indent: int = 2) -> None:
    """Pretty-print a flat/nested dict for the CLI."""
    pad = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{pad}{key}:")
            print_kv(value, indent + 4)
        elif isinstance(value, list):
            print(f"{pad}{key}:")
            for item in value:
                print(f"{pad}  - {item}")
        else:
            print(f"{pad}{key}: {value}")


def env(name: str) -> str:
    """Read an environment variable (works with or without python-dotenv)."""
    return os.getenv(name, "").strip()
