"""
    Configuration which we're planning to load from the environment variables (.env) ! 
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token:  str
    owner_chat_id: int                 # our telegram chat id 
    timezone: ZoneInfo
    db_path: str
    default_celebration_time: str       # "HH:MM" ---- moment of bday
# starts
    tick_seconds: int                   # how often should the scheduler checks for the due reminders 
# due reminders
    grace_minutes: int                  # how late a remidner may still fire 
# (after downtime)

def _env(key: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Missing Required Environment Variables: {key}")
    return value or ""

def load_config() -> Config:
    return Config(
        bot_token=_env("BOT_TOKEN", required=True),
        owner_chat_id = int(_env("OWNER_CHAT_ID", "0")),
        timezone=ZoneInfo(_env("TIMEZONE", "Asia/Kolkata")),
        db_path=_env("DB_PATH", "data/birthdays.db"),
        default_celebration_time=_env("DEFAULT_CELEBRATION_TIME", "09:00"),
        tick_seconds=int(_env("TICK_SECONDS", "60")),
        grace_minutes=int(_env("GRACE_MINUTES", "120")),
    )

config = load_config()