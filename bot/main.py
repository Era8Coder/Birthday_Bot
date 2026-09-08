"""
    It's the entry point of the entire thing 
    wires config
    database
    handlers
    reminder tick 
    altogether :)))
"""
from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from . import handlers
from .config import config
from .db import Database
from .scheduler import housekeeping, tick

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level = logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("birthday-bot")

def build_app() -> Application:
    app = Application.builder().token(config.bot_token).build()

    ## Shared state available to every handler and job via context.bot_data !! 
    app.bot_data.update(
        db = Database(config.db_path),
        tz = config.timezone,
        default_time = config.default_celebration_time,
        grace_minutes = config.grace_minutes,
    )

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_cmd))
    app.add_handler(CommandHandler("add", handlers.add))
    app.add_handler(CommandHandler("list", handlers.list_cmd))
    app.add_handler(CommandHandler("upcoming", handlers.upcoming))
    app.add_handler(CommandHandler("today", handlers.today))
    app.add_handler(CommandHandler("settime", handlers.settime))
    app.add_handler(CommandHandler("delete", handlers.delete))
    app.add_handler(CommandHandler("test", handlers.test))
    app.add_error_handler(handlers.on_error)

    # Creating a Reminder wngine which will check every minute what's going on !!
    app.job_queue.run_repeating(tick, interval=config.tick_seconds, first=5, name="reminder-tick")
    app.job_queue.run_repeating(housekeeping, interval=86400, first=60, name = "housekeeping")

    return app

def main() -> None:
    log.info("Starting bot (timezone=%s, db=%s)", config.timezone, config.db_path)
    build_app().run_polling(drop_pending_updates = True)

if __name__ == "__main__":
    main()