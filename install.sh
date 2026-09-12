#!/usr/bin/env bash
#
# install.sh — one-shot setup for ORF-5 on Linux, macOS, or Termux.
# Usage: bash install.sh

set -euo pipefail

GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
say()  { printf "${GREEN}[orf5]${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}[orf5]${RESET} %s\n" "$*"; }
die()  { printf "${RED}[orf5]${RESET} %s\n" "$*" >&2; exit 1; }

cd "$(dirname "$0")"

# --- figure out where we are -------------------------------------------------
OS="linux"
if [ "$(uname -s)" = "Darwin" ]; then OS="macos"; fi
if [ -n "${PREFIX:-}" ] && [[ "$PREFIX" == *com.termux* ]]; then OS="termux"; fi
say "Detected environment: $OS"

# --- system python -------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  case "$OS" in
    termux)
      warn "Python not found — installing via pkg …"
      pkg update -y && pkg install -y python
      ;;
    macos)
      die "Python 3 not found. Install it with: brew install python"
      ;;
    linux)
      if command -v apt >/dev/null 2>&1; then
        warn "Installing python3 + venv via apt (may ask for sudo) …"
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip
      else
        die "Python 3 not found. Install it with your distro's package manager and re-run."
      fi
      ;;
  esac
fi
say "Using $(python3 --version)"

# --- virtualenv ------------------------------------------------------------------
if [ ! -d .venv ]; then
  say "Creating virtual environment (.venv) …"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

say "Upgrading pip …"
python -m pip install --quiet --upgrade pip

say "Installing Python dependencies …"
pip install --quiet -r requirements.txt

# --- env file ----------------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  say "Created .env — add your tokens there before using the Telegram bot / PUBG module."
else
  say ".env already exists — leaving it untouched."
fi

echo
say "Done. Quick start:"
echo "    source .venv/bin/activate"
echo "    python main.py username octocat"
echo
say "If ORF-5 is useful to you, consider leaving a star on the repo. ⭐"
