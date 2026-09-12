# ORF-5 — Asynchronous 5-in-1 OSINT & Reconnaissance Framework

Cross-platform (Windows 10/11, Zorin OS / any Linux), built on **asyncio + aiohttp**
for high-speed, concurrent, non-blocking network requests.

## Components

| # | Module | File | What it does |
|---|--------|------|--------------|
| 1 | Username Recon | `modules/username_recon.py` | Verifies profile existence across social/gaming networks via HTTP status codes; platforms fully configurable in `config/platforms.json` |
| 2 | Game Stats Inspector | `modules/game_stats.py` | Fetches public player data by UID/name (Free Fire MAX via public stats API, PUBG via official developer API) |
| 3 | Metadata Extractor | `modules/metadata_extractor.py` | Scrapes Open Graph / Twitter Card / meta tags (og:image, og:description, …) with BeautifulSoup4 — no auth required |
| 4 | Breach Exposure Checker | `modules/breach_checker.py` | k-Anonymity SHA-1 range queries against HaveIBeenPwned (only the 5-char hash prefix leaves the machine); optional HIBP account API with key |
| 5 | Dual Interface | `interfaces/cli.py` + `interfaces/telegram_bot.py` | Full argparse CLI and an asynchronous aiogram 3 Telegram bot |

The core engine (`core/engine.py`) provides pooled connections, randomized
User-Agents, strict timeouts, bounded concurrency, retries with jittered
backoff, and graceful handling of blocked (401/403/429/451/503) endpoints.

## Install

```bash
git clone <this-repo> && cd osint-recon-framework
python -m venv .venv
# Linux / Zorin OS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in tokens/keys
```

Requires Python **3.9+**.

## CLI usage

```bash
python main.py username octocat
python main.py username octocat --only github,steam --output results/report.json
python main.py gamestats --game freefire --id 1234567890
python main.py gamestats --game pubg --id "SomePlayer" --shard steam
python main.py metadata https://github.com/octocat
python main.py breach someone@example.com
python main.py bot                       # start Telegram interface
```

Global engine flags: `--timeout`, `--connect-timeout`, `--concurrency`, `--retries`.

## Telegram bot

1. Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.
2. Put it in `.env` as `TELEGRAM_BOT_TOKEN` (or pass `--token`).
3. `python main.py bot`
4. In Telegram: `/start`, `/username octocat`, `/gamestats freefire 1234567890`,
   `/metadata https://github.com/octocat`, `/breach someone@example.com`.

## API keys (optional)

| Key | Env var | Needed for |
|-----|---------|-----------|
| PUBG developer key (free) | `PUBG_API_KEY` | PUBG player lookups |
| HIBP API key (paid) | `HIBP_API_KEY` | e-mail breach-account detail (k-anonymity check needs no key) |

## Adding platforms

Edit `config/platforms.json`. Each entry supports `url` (`{username}` placeholder),
`method`, `headers`, and match rules: `found_status`, `not_found_status`,
`body_contains`, `body_not_contains` (case-insensitive). No code changes needed.

## Legal & ethical notice

This framework queries **publicly available data only**. Use it exclusively on
accounts/data you own or are authorized to investigate, respect each site's
Terms of Service, and comply with local privacy laws (e.g. IT Act / DPDP Act
in India, GDPR in the EU). Do not use it for stalking, harassment, or
unauthorized surveillance.
