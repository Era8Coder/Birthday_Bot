"""
    SQLite persistence layer, which is small synchronous and dependency-free
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .models import Birthday

SCHEMA = """
CREATE TABLE IF NOT EXISTS birthdays (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id             INTEGER NOT NULL,
    name                TEXT NOT NULL,
    day                 INTEGER NOT NULL,
    month               INTEGER NOT NULL,
    year                INTEGER,
    celebration_time    TEXT NOT NULL DEFAULT "09:00",
    note                TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_birthdays_chat
ON birthdays(chat_id);

CREATE TABLE IF NOT EXISTS sent_reminders (
    birthday_id INTEGER NOT NULL,
    year        INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    sent_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (birthday_id, year, kind),
    FOREIGN KEY (birthday_id)
        REFERENCES birthdays(id)
        ON DELETE CASCADE
);
"""

class Database: 
    def __init__(self, path: str) -> None:
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # <><><><><><><><><><><> Birthdays <><><><><><><><><><><>
    def add_birthday(
        self,
        chat_id: int,
        name: str,
        day: int,
        month: int,
        year: int | None, 
        celebration_time: str,
        note: str | None = None,
    ) -> int: 
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO birthdays (chat_id, name, day, month, year, celebration_time, note)
                    VALUES (?,?,?,?,?,?,?)""",
                (chat_id, name, day, month, year, celebration_time, note),
            )

            return int(cur.lastrowid)
        
    def delete_birthday(self, chat_id: int, birthday_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute (
                "DELETE FROM birthdays WHERE id = ? AND chat_id = ?",
                (birthday_id, chat_id)
            )

            return cur.rowcount > 0
        
    def list_birthdays(self, chat_id: int) -> list[Birthday]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM birthdays " \
                "WHERE chat_id = ? " \
                "ORDER BY month, day", (chat_id, )
            ).fetchall()

            return [self._row_to_birthday(r) for r in rows]
        
    def all_birthdays(self) -> list[Birthday]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM birthdays"
            ).fetchall()
            
            return [self._row_to_birthday(r) for r in rows]
        
    def update_time(self, chat_id: int, birthday_id: int, celebration_time: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE birthdays SET celebration_time = ? WHERE id = ? AND chat_id = ?",
                (celebration_time, birthday_id, chat_id)
            )
            return cur.rowcount > 0
    
    # <><><><><><><><><><><> Dedupe <><><><><><><><><><><>  // finding or removing extra copies from the list <--- 
    def already_sent(self, birthday_id: int, year: int, kind: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM sent_reminders WHERE birthday_id = ? AND year = ? AND kind = ?",
                (birthday_id, year, kind),
            ).fetchone()
            return row is not None
        
    def mark_sent(self, birthday_id: int, year: int, kind: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO sent_reminders 
                    (birthday_id, year, kind)
                    VALUES (?, ?, ?)""",
                    (birthday_id, year, kind),
            )

    def prune_sent(self, keep_year: int) -> None:
        """Housekeeping: drop dedupe rows older than the previous year."""
        with self._conn() as conn:
            conn.execute("DELETE FROM sent_reminders WHERE year < ?", (keep_year - 1,))

    # <><><><><><><><><><><> Mapping <><><><><><><><><><><>
    @staticmethod
    def _row_to_birthday(row: sqlite3.Row) -> Birthday:
        return Birthday (
            id = row["id"],
            chat_id = row["chat_id"],
            name = row["name"],
            day=row["day"],
            month = row["month"],
            year=row["year"],
            celebration_time=row["celebration_time"],
            note = row["note"],
        )

    