# Changelog

## v1.1.0 — 2026-09-12

- One-shot installers for every environment: `install.sh` (Linux / macOS / Termux),
  `install.bat` (cmd), `install.ps1` (PowerShell / Windows Terminal)
- README overhaul: per-platform install guides (Termux, Zorin/Debian, Fedora, Arch, macOS,
  Windows), troubleshooting notes, roadmap
- `python main.py --version` now works
- MIT license + contributing guide added

## v1.0.0 — 2026-09-11

- Initial release: username recon (20 platforms), game stats (Free Fire MAX / PUBG),
  Open Graph metadata extractor, k-anonymity breach checker
- CLI (argparse) + Telegram bot (aiogram 3)
- Async core engine: pooled aiohttp session, UA rotation, timeouts, retries, throttling
