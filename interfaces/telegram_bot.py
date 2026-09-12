"""interfaces/telegram_bot.py — asynchronous Telegram interface (aiogram 3.x).

Start it with:
    python main.py bot --token <TOKEN>
or set TELEGRAM_BOT_TOKEN in a .env file and run `python main.py bot`.

Commands:
    /start, /help                     usage
    /username <handle>                cross-platform username scan
    /gamestats <game> <uid|name>      freefire <uid> | pubg <player name>
    /metadata <url>                   Open Graph extraction
    /breach <email|username>          k-anonymity breach check
"""
from __future__ import annotations

import html
import logging
from typing import List

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from core.engine import ReconEngine
from core.utils import chunk_text
from modules import breach_checker, game_stats, metadata_extractor, username_recon

logging.basicConfig(level=logging.INFO, format="%(asctime)s aiogram %(levelname)s %(message)s")
router = Router(name="orf5")

HELP_TEXT = (
    "<b>ORF-5 — OSINT Recon Bot</b>\n\n"
    "<b>Commands</b>\n"
    "/username &lt;handle&gt; — scan a username across social &amp; gaming platforms\n"
    "/gamestats &lt;game&gt; &lt;id&gt; — game: <code>freefire</code> (numeric UID) or <code>pubg</code> (player name)\n"
    "/metadata &lt;url&gt; — extract Open Graph tags from a public page\n"
    "/breach &lt;email|username&gt; — k-anonymity breach exposure check\n\n"
    "<i>Only public data is queried. Use responsibly.</i>"
)

_STATE_ICONS = {
    username_recon.FOUND: "✅",
    username_recon.NOT_FOUND: "❌",
    username_recon.BLOCKED: "🚫",
    username_recon.UNKNOWN: "❓",
    username_recon.ERROR: "⚠️",
}


def _esc(value: object) -> str:
    return html.escape(str(value), quote=False)


async def _send_long(message: Message, text: str) -> None:
    for chunk in chunk_text(text, 4000):
        await message.answer(chunk)


# --------------------------------------------------------------------------
# basic commands
# --------------------------------------------------------------------------
@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


# --------------------------------------------------------------------------
# /username <handle>
# --------------------------------------------------------------------------
@router.message(Command("username"))
async def cmd_username(message: Message, command: CommandObject) -> None:
    username = (command.args or "").strip().lstrip("@")
    if not username:
        await message.answer("Usage: /username &lt;handle&gt;")
        return

    status = await message.answer(f"🔎 Scanning <b>{_esc(username)}</b> … please wait.")
    try:
        async with ReconEngine(max_concurrency=15) as engine:
            results = await username_recon.scan(engine, username)
    except Exception as exc:  # noqa: BLE001
        await status.edit_text(f"⚠️ Scan failed: {_esc(exc)}")
        return

    summary = username_recon.summarize(results)
    lines: List[str] = [
        f"<b>Username scan: {_esc(username)}</b>",
        "  ".join(f"{k}: {v}" for k, v in sorted(summary.items())),
        "",
    ]
    for r in results:
        icon = _STATE_ICONS.get(r.state, "❓")
        detail = f"HTTP {r.status}" if r.status else _esc(r.error or "n/a")
        lines.append(f"{icon} <b>{_esc(r.platform)}</b> — {r.state} ({detail})\n    <code>{_esc(r.url)}</code>")

    await status.delete()
    await _send_long(message, "\n".join(lines))


# --------------------------------------------------------------------------
# /gamestats <game> <identifier>
# --------------------------------------------------------------------------
@router.message(Command("gamestats"))
async def cmd_gamestats(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Usage: /gamestats &lt;freefire|pubg&gt; &lt;uid or player name&gt;")
        return
    game, identifier = parts[0].strip().lower(), parts[1].strip()

    status = await message.answer(f"🎮 Looking up <b>{_esc(game)}</b> player <b>{_esc(identifier)}</b> …")
    try:
        async with ReconEngine() as engine:
            report = await game_stats.lookup(engine, game, identifier)
    except Exception as exc:  # noqa: BLE001
        await status.edit_text(f"⚠️ Lookup failed: {_esc(exc)}")
        return

    if report.get("error") or not report.get("found"):
        await status.edit_text(f"⚠️ {_esc(report.get('error') or 'No public data found for this identifier.')}")
        return

    lines = [f"<b>{_esc(report['game'])}</b> — public profile ({_esc(report.get('provider', 'n/a'))})"]
    data = report.get("data", {})
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"• <b>{_esc(key)}</b>: {_esc(value)}")
            elif isinstance(value, list):
                lines.append(f"• <b>{_esc(key)}</b>:")
                for item in value:
                    lines.append(f"    <code>{_esc(item)}</code>")
    await status.edit_text("\n".join(lines)[:4000])


# --------------------------------------------------------------------------
# /metadata <url>
# --------------------------------------------------------------------------
@router.message(Command("metadata"))
async def cmd_metadata(message: Message, command: CommandObject) -> None:
    url = (command.args or "").strip()
    if not url.startswith(("http://", "https://")):
        await message.answer("Usage: /metadata &lt;https://example.com/profile&gt;")
        return

    status = await message.answer(f"📄 Extracting metadata from <code>{_esc(url)}</code> …")
    try:
        async with ReconEngine() as engine:
            report = await metadata_extractor.extract(engine, url)
    except Exception as exc:  # noqa: BLE001
        await status.edit_text(f"⚠️ Extraction failed: {_esc(exc)}")
        return

    if report.get("error"):
        await status.edit_text(f"⚠️ {_esc(report['error'])}")
        return

    lines = [f"<b>Metadata</b> — <code>{_esc(url)}</code>"]
    if report.get("title"):
        lines.append(f"• <b>title</b>: {_esc(report['title'])}")
    for key, value in (report.get("metadata") or {}).items():
        lines.append(f"• <b>{_esc(key)}</b>: {_esc(value)}")
    await status.delete()
    await _send_long(message, "\n".join(lines))


# --------------------------------------------------------------------------
# /breach <email|username>
# --------------------------------------------------------------------------
@router.message(Command("breach"))
async def cmd_breach(message: Message, command: CommandObject) -> None:
    identifier = (command.args or "").strip()
    if not identifier:
        await message.answer("Usage: /breach &lt;email or username&gt;")
        return

    status = await message.answer(f"🔐 Checking <b>{_esc(identifier)}</b> via k-anonymity …")
    try:
        async with ReconEngine() as engine:
            report = await breach_checker.check_identifier(engine, identifier)
    except Exception as exc:  # noqa: BLE001
        await status.edit_text(f"⚠️ Check failed: {_esc(exc)}")
        return

    k = report["k_anonymity"]
    if k["exposed"] is None:
        await status.edit_text("⚠️ k-anonymity lookup failed. Try again later.")
        return

    if k["exposed"]:
        text = (f"🚨 <b>EXPOSED</b>\n{_esc(identifier)} appears in the HIBP breached-data corpus "
                f"(up to {k['max_occurrences']} occurrence(s)).\nSHA-1: <code>{k['candidates'][0]['sha1']}</code>")
    else:
        text = (f"✅ <b>NO MATCH</b>\n{_esc(identifier)} was not found in the HIBP breached-data corpus.\n"
                f"SHA-1: <code>{k['candidates'][0]['sha1']}</code>")
    await status.edit_text(text)


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------
async def run_bot(token: str) -> None:
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
