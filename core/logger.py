"""core/logger.py — tiny colored console logger that works on Windows and Linux."""
from __future__ import annotations

import sys

try:
    from colorama import init as _colorama_init

    _colorama_init()
    from colorama import Fore, Style

    C = {
        "info": Fore.CYAN,
        "ok": Fore.GREEN,
        "warn": Fore.YELLOW,
        "error": Fore.RED,
        "step": Fore.MAGENTA,
        "reset": Style.RESET_ALL,
        "bold": Style.BRIGHT,
    }
except Exception:  # pragma: no cover — colorama missing or broken terminal
    C = {k: "" for k in ("info", "ok", "warn", "error", "step", "reset", "bold")}


def _emit(color: str, tag: str, msg: str) -> None:
    print(f"{C[color]}{tag}{C['reset']} {msg}", flush=True)


def info(msg: str) -> None:
    _emit("info", "[*]", msg)


def ok(msg: str) -> None:
    _emit("ok", "[+]", msg)


def warn(msg: str) -> None:
    _emit("warn", "[!]", msg)


def error(msg: str) -> None:
    _emit("error", "[-]", msg)


def step(msg: str) -> None:
    _emit("step", "[>]", msg)


def banner() -> None:
    art = rf"""
{C['bold']}{C['step']}
   ___  ____  _____   ____
  / _ \|  _ \|  ___| |___ \
 | | | | |_) | |_      __) |
 | |_| |  _ <|  _|    / __/
  \___/|_| \_\_|     |_____|

  ORF-5 · Async OSINT & Reconnaissance Framework
  username · gamestats · metadata · breach · telegram
{C['reset']}"""
    print(art, file=sys.stderr)
