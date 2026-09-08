"""
    Reminder Engine <-------
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from .db import Database
from .models import(
    KIND_DAY_BEFORE, 
    KIND_HALF_HOUR,
    Birthday, 
    DueReminder, 
    reminder_times,
)

log = logging.getLogger(__name__)

def collect_due(
    db: Database, now: datetime, tz: ZoneInfo, grace: timedelta 
) -> list[DueReminder]:
    due : list[DueReminder] = []

    for bd in db.all_birthdays():
        for year in (now.year, now.year+1):
            occurrence = bd.occurrence(year, tz)
            for kind, fire_at in reminder_times(bd, occurrence).items():
                if not (now - grace <= fire_at <= now):
                    continue
                
                if db.already_sent(bd.id, year, kind):
                    continue

                due.append(DueReminder(birthday=bd, kind=kind, year=year, fire_at=fire_at))

    return sorted(due, key=lambda d: d.fire_at)

def build_message(bd: Birthday, kind: str, year: int) -> str:
    age = bd.age_turning(year)
    age_txt = f" - turning <b>{age}</b>" if age is not None else ""
    note = f"\n\n {bd.note}" if bd.note else ""

    if kind == KIND_DAY_BEFORE:
        return (
            f" <b>Tomorrow: </b> {bd.name}'s Birthday{age_txt}.\n"
            f"Time to sort out gift or message.{note}"
        )
    
    return (
        f" <b> In 30 minutes:</b> {bd.name}'s Birthday{age_txt}.\n"
        f"Get that wish ready! {note}"
    )

async def tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    """ JobCallBack registered on the PTB JobQueue"""
    db: Database = context.bot_data["db"]
    tz: ZoneInfo = context.bot_data["tz"]
    grace = timedelta(minutes=context.bot_data["grace_minutes"])

    now = datetime.now(tz)
    due = collect_due(db, now, tz, grace)

    for item in due:
        try:
            await context.bot.send_message(
                chat_id = item.birthday.chat_id,
                text = build_message(item.birthday, item.kind, item.year),
                parse_mode="HTML",
            )
            db.mark_sent(item.birthday.id, item.year, item.kind)
            log.info("Sent %s reminder for %s", item.kind, item.birthday.name)

        except Exception:
            log.exception("Failed to send reminder for birthday id=%s", item.birthday.id)

async def housekeeping(context: ContextTypes.DEFAULT_TYPE) -> None:
    db: Database = context.bot_data["db"]
    tz: ZoneInfo = context.bot_data["tz"]
    db.prune_sent(datetime.now(tz).year)
