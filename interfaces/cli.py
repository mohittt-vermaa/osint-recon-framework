"""interfaces/cli.py — comprehensive command-line interface (argparse).

Subcommands:
    username    scan a username across all configured platforms
    gamestats   fetch public player stats (Free Fire MAX, PUBG)
    metadata    extract Open Graph / meta tags from a public page
    breach      k-anonymity breach exposure check
    bot         launch the Telegram interface
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import List, Optional

try:  # optional .env support
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from core import __version__, logger
from core.engine import ReconEngine
from core.utils import REPO_ROOT, RESULTS_DIR, save_json
from modules import breach_checker, game_stats, metadata_extractor, username_recon

STATE_ICONS = {
    username_recon.FOUND: "+",
    username_recon.NOT_FOUND: "-",
    username_recon.BLOCKED: "!",
    username_recon.UNKNOWN: "?",
    username_recon.ERROR: "x",
}

EXAMPLES = """examples:
  python main.py username octocat
  python main.py username octocat --only github,steam --output results/u.json
  python main.py gamestats --game freefire --id 1234567890
  python main.py gamestats --game pubg --id "PlayerName" --shard steam
  python main.py metadata https://github.com/octocat
  python main.py breach someone@example.com
  python main.py bot --token 123456:ABC...
"""


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orf",
        description="ORF-5 — asynchronous 5-in-1 OSINT & reconnaissance framework.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"ORF-5 {__version__}")
    parser.add_argument("--timeout", type=float, default=15.0, help="total request timeout in seconds (default: 15)")
    parser.add_argument("--connect-timeout", type=float, default=8.0, help="connect timeout in seconds (default: 8)")
    parser.add_argument("--concurrency", type=int, default=20, help="max parallel requests (default: 20)")
    parser.add_argument("--retries", type=int, default=2, help="retries per failed request (default: 2)")

    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_user = sub.add_parser("username", help="scan a username across social/gaming platforms")
    p_user.add_argument("username", help="the handle to search for")
    p_user.add_argument("--platforms", default=None, help="custom platforms JSON file")
    p_user.add_argument("--only", default=None, help="comma-separated platform names to include")
    p_user.add_argument("--output", default=None, help="write JSON report to this file")

    p_game = sub.add_parser("gamestats", help="fetch public player stats")
    p_game.add_argument("--game", required=True, choices=["freefire", "pubg"], help="game title")
    p_game.add_argument("--id", dest="identifier", required=True, help="numeric UID (Free Fire) or player name (PUBG)")
    p_game.add_argument("--shard", default="steam", help="PUBG shard: steam | xbox | console (default: steam)")
    p_game.add_argument("--lang", default="en", help="Free Fire language code (default: en)")

    p_meta = sub.add_parser("metadata", help="extract Open Graph / meta tags from a public URL")
    p_meta.add_argument("url", help="public profile or page URL")
    p_meta.add_argument("--output", default=None, help="write JSON report to this file")

    p_breach = sub.add_parser("breach", help="k-anonymity breach exposure check")
    p_breach.add_argument("identifier", help="e-mail address or username")
    p_breach.add_argument("--kind", choices=["auto", "email", "username"], default="auto")
    p_breach.add_argument("--output", default=None, help="write JSON report to this file")

    p_bot = sub.add_parser("bot", help="start the Telegram bot interface")
    p_bot.add_argument("--token", default=None, help="bot token (else TELEGRAM_BOT_TOKEN env/.env)")

    return parser


def engine_from_args(args: argparse.Namespace) -> ReconEngine:
    return ReconEngine(
        max_concurrency=args.concurrency,
        total_timeout=args.timeout,
        connect_timeout=args.connect_timeout,
        retries=args.retries,
    )


def _maybe_save(path: Optional[str], data) -> None:
    if path:
        saved = save_json(path, data)
        logger.info(f"Report saved to {saved}")


# --------------------------------------------------------------------------
# command handlers
# --------------------------------------------------------------------------
async def cmd_username(args: argparse.Namespace) -> int:
    username = args.username.strip().lstrip("@")
    if not username:
        logger.error("Empty username.")
        return 2

    platforms_path = args.platforms or None
    try:
        platforms = username_recon.load_platforms(platforms_path) if platforms_path \
            else username_recon.load_platforms()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Cannot load platforms file: {exc}")
        return 2

    if args.only:
        wanted = {w.strip().lower() for w in args.only.split(",") if w.strip()}
        platforms = [p for p in platforms if p["name"].lower() in wanted]
        if not platforms:
            logger.error("--only matched no known platforms.")
            return 2

    logger.info(f"Scanning username '{username}' across {len(platforms)} platforms …")

    async def progress(r: username_recon.PlatformResult) -> None:
        icon = STATE_ICONS.get(r.state, "?")
        suffix = f"HTTP {r.status}" if r.status else (r.error or "n/a")
        logger.step(f"[{icon}] {r.platform:<18} {r.state:<10} ({suffix}, {r.elapsed_ms} ms)  {r.url}")

    async with engine_from_args(args) as engine:
        results = await username_recon.scan(engine, username, platforms, progress_cb=progress)

    summary = username_recon.summarize(results)
    print()
    logger.ok(f"Done. " + "  ".join(f"{k}: {v}" for k, v in sorted(summary.items())))
    found = [r for r in results if r.state == username_recon.FOUND]
    if found:
        logger.ok("Profiles found:")
        for r in found:
            print(f"      {r.url}")

    _maybe_save(args.output, {"username": username, "summary": summary,
                              "results": [r.to_dict() for r in results]})
    return 0


async def cmd_gamestats(args: argparse.Namespace) -> int:
    logger.info(f"Looking up {args.game} player '{args.identifier}' …")
    async with engine_from_args(args) as engine:
        report = await game_stats.lookup(
            engine, args.game, args.identifier, shard=args.shard, lang=args.lang
        )
    print()
    if report.get("error"):
        logger.error(report["error"])
        return 1
    if not report.get("found"):
        logger.warn("No public profile data returned for this identifier.")
        return 1

    logger.ok(f"{report['game']} public profile ({report.get('provider', 'n/a')}):")
    from core.utils import print_kv

    print_kv(report.get("data", {}), indent=4)
    return 0


async def cmd_metadata(args: argparse.Namespace) -> int:
    logger.info(f"Extracting metadata from {args.url} …")
    async with engine_from_args(args) as engine:
        report = await metadata_extractor.extract(engine, args.url)
    print()
    if report.get("error"):
        logger.error(report["error"])
        return 1

    logger.ok(f"Title: {report.get('title') or '(none)'}")
    if report.get("canonical"):
        logger.info(f"Canonical: {report['canonical']}")
    metadata = report.get("metadata", {})
    if metadata:
        from core.utils import print_kv

        print_kv(metadata, indent=2)
    else:
        logger.warn("No Open Graph / meta tags found on this page.")
    _maybe_save(args.output, report)
    return 0


async def cmd_breach(args: argparse.Namespace) -> int:
    logger.info(f"Checking breach exposure for '{args.identifier}' (k-anonymity, no plaintext leaves this machine) …")
    async with engine_from_args(args) as engine:
        report = await breach_checker.check_identifier(
            engine, args.identifier, kind=args.kind
        )
    print()
    k = report["k_anonymity"]
    if k["exposed"] is None:
        logger.error("k-anonymity lookup failed: " + "; ".join(report.get("errors", ["unknown"])))
        return 1
    if k["exposed"]:
        logger.warn(f"EXPOSED — value appears in the HIBP breached-data corpus "
                    f"(up to {k['max_occurrences']} occurrence(s)).")
    else:
        logger.ok("No match found in the HIBP breached-data corpus.")

    account = report.get("account_lookup")
    if account:
        if account.get("error"):
            logger.warn(f"Account lookup: {account['error']}")
        elif account.get("breaches"):
            logger.warn("Account found in breaches: " + ", ".join(account["breaches"]))
        else:
            logger.ok("Account not listed in any HIBP breach.")

    _maybe_save(args.output, report)
    return 0


async def cmd_bot(args: argparse.Namespace) -> int:
    import os

    from interfaces.telegram_bot import run_bot

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.error("No bot token. Pass --token or set TELEGRAM_BOT_TOKEN in .env")
        return 2
    logger.info("Starting Telegram bot (Ctrl+C to stop) …")
    try:
        await run_bot(token)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Bot stopped: {exc}")
        return 1
    return 0


# --------------------------------------------------------------------------
# dispatcher
# --------------------------------------------------------------------------
HANDLERS = {
    "username": cmd_username,
    "gamestats": cmd_gamestats,
    "metadata": cmd_metadata,
    "breach": cmd_breach,
    "bot": cmd_bot,
}


async def run_cli(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)

    logger.banner()
    handler = HANDLERS[args.command]
    return await handler(args)
