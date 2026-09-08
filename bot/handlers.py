from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .db import Database
from .models import KIND_DAY_BEFORE, KIND_HALF_HOUR, Birthday
from .scheduler import build_message
from .utils import ParseError, escape_html, parse_add_command, parse_time

log = logging.getLogger(__name__)
HELP = """🎂 <b>Birthday Reminder Bot</b>

I ping you <b>1 day before</b> and <b>30 minutes before</b> every birthday you save.

<b>Commands</b>
/add — <code>/add Riya | 14-03-1998 | 09:00</code>
Year and time are optional (time defaults to your configured one).
/list — all saved birthdays, sorted by date
/upcoming — the next 30 days
/today — whose birthday is today
/settime — <code>/settime 3 08:30</code> changes the time for entry #3
/delete — <code>/delete 3</code> removes entry #3
/test — sends you a sample of both reminders
/help — this message

<b>Date formats I understand</b>
14-03-1998 · 14/03 · 14.03.1998 · "14 Mar"
"""

def _tz(context: ContextTypes.DEFAULT_TYPE) -> ZoneInfo:
    return context.bot_data["tz"]

def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.bot_data["db"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        f"Hi! Your chat id is <code>{update.effective_chat.id}</code>.\n\n{HELP}"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP)

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db, tz = _db(context), _tz(context)
    try:
        name, day, month, year, celebration_time = parse_add_command(
            update.message.text, context.bot_data["default_time"]
        )
    
    except ParseError as exc:
        await update.message.reply_html(f"⚠️ {exc}")
        return
 
    bid = db.add_birthday(
    chat_id=update.effective_chat.id,
    name=name,
    day=day,
    month=month,
    year=year,
    celebration_time=celebration_time,
    )

    bd = Birthday(bid, update.effective_chat.id, name, day, month, year, celebration_time)
    now = datetime.now(tz)
    occ = bd.next_occurrence(now, tz)

    await update.message.reply_html(
        f"✅ Saved <b>{escape_html(name)}</b> — {occ.strftime('%d %b')} at {celebration_time}.\n"
        f"I'll remind you on {(occ - timedelta(days=1)).strftime('%d %b at %H:%M')} "
        f"and again 30 minutes before."
    )

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db, tz = _db(context), _tz(context)
    rows = db.list_birthdays(update.effective_chat.id)
    
    if not rows:
        await update.message.reply_html("Nothing saved yet. Add one with /add.")
        
        return

    now = datetime.now(tz)
    body = "\n\n".join(bd.pretty(now, tz) for bd in rows)

    await update.message.reply_html(f"📒 <b>Saved birthdays ({len(rows)})</b>\n\n{body}")

async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db, tz = _db(context), _tz(context)
    now = datetime.now(tz)
    rows = [b for b in db.list_birthdays(update.effective_chat.id) if b.days_until(now, tz) <= 30]
    rows.sort(key=lambda b: b.days_until(now, tz))

    if not rows:
        await update.message.reply_html("No birthdays in the next 30 days. 🎈")

        return

    body = "\n\n".join(bd.pretty(now, tz) for bd in rows)
    await update.message.reply_html(f"📅 <b>Next 30 days</b>\n\n{body}")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db, tz = _db(context), _tz(context)
    now = datetime.now(tz)
    rows = [b for b in db.list_birthdays(update.effective_chat.id) if b.days_until(now, tz) == 0]
    if not rows:
        await update.message.reply_html("No birthdays today.")
        return

    body = "\n\n".join(bd.pretty(now, tz) for bd in rows)
    await update.message.reply_html(f"🎉 <b>Today</b>\n\n{body}")

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    if len(context.args) != 2:  
        await update.message.reply_html("Usage: <code>/settime 3 08:30</code>")
        return

    try:
        bid = int(context.args[0])
        new_time = parse_time(context.args[1])
    
    except (ValueError, ParseError) as exc:
        await update.message.reply_html(f"⚠️ {exc}")
        return

    ok = db.update_time(update.effective_chat.id, bid, new_time)

    await update.message.reply_html(
        f"✅ Entry #{bid} now celebrates at {new_time}." if ok else f"❌ No entry #{bid}."
    )

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_html("Usage: <code>/delete 3</code>")
        return

    bid = int(context.args[0])
    ok = db.delete_birthday(update.effective_chat.id, bid)
    await update.message.reply_html(f"🗑 Deleted #{bid}." if ok else f"❌ No entry #{bid}.")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Preview both reminder messages without waiting for a real birthday."""
    tz = _tz(context)
    sample = Birthday(0, update.effective_chat.id, "Sample Friend", 1, 1, 1998, "09:00")
    year = datetime.now(tz).year
    await update.message.reply_text(
    build_message(sample, KIND_DAY_BEFORE, year), parse_mode=ParseMode.HTML
)

    await update.message.reply_text(
    build_message(sample, KIND_HALF_HOUR, year), parse_mode=ParseMode.HTML
)

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Unhandled error", exc_info=context.error)