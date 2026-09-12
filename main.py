#!/usr/bin/env python3
"""ORF-5 — entry point.

Usage:
    python main.py username octocat
    python main.py gamestats --game freefire --id 123456789
    python main.py metadata https://github.com/octocat
    python main.py breach someone@example.com
    python main.py bot                      # start the Telegram interface
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make sure the repository root is importable no matter where we are launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    # Windows: the selector loop is the most reliable policy for aiohttp/aiogram.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Force UTF-8 consoles (Windows cmd.exe chokes on Unicode otherwise).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    from interfaces.cli import run_cli

    try:
        raise SystemExit(asyncio.run(run_cli(sys.argv[1:])))
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user. Exiting cleanly.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
