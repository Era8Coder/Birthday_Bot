"""Parsing helpers for user input <-- """
from __future__ import annotations

import re
from datetime import datetime
from html import escape

DATE_PATTERNS = (
    "%d %B %Y",       # 25 August 2001
    "%d %B",          # 25 August

    "%d %b %Y",       # 25 Aug 2001
    "%d %b",          # 25 Aug

    "%d-%m-%Y",       # 25-08-2001
    "%d-%m-%y",       # 25-08-01

    "%d/%m/%Y",       # 25/08/2001
    "%d/%m/%y",       # 25/08/01

    "%d.%m.%Y",       # 25.08.2001
    "%d.%m.%y",       # 25.08.01

    "%Y-%m-%d",       # 2001-08-25
    "%Y/%m/%d",       # 2001/08/25
)
TIME_RE = re.compile(
    r"""
    ^\s*
    (?P<hour>1[0-2]|0?[1-9]|2[0-3])
    (?:
        :
        (?P<minute>[0-5][0-9])
    )?
    \s*
    (?P<ampm>[AaPp][Mm])?
    \s*$
    """,
    re.VERBOSE,
)

class ParseError(ValueError):
    """Raise when the user's input can't be understood"""
    pass

def parse_date(raw: str) -> tuple[int, int, int | None]:
    """Return (day, month, year|None) from commonly used date patters"""
    raw = raw.strip()
    for fmt in DATE_PATTERNS:
        try:
            dt = datetime.strptime(raw, fmt)
        except ValueError: 
            continue
        has_year = "%Y" in fmt
        return dt.day, dt.month, (dt.year if has_year else None)
    
    raise ParseError(
        f"Could not read the date '{raw}'. Try 06-05-2005 or 6th May."
    )

def parse_time(raw: str) -> str:
    raw = raw.strip()
    if not TIME_RE.match(raw):
        raise ParseError(f"Could not read the time '{raw}'. Use 24h format like 19:00.")
    
    hh, mm = raw.split(":")
    return f"{int(hh):02d}:{mm}"

def parse_add_command(text: str, default_time: str) -> tuple[str, int, int, int|None, str]:
    """
    Parse: /add Name | DD-MM-YYYY | HH:MM
    Pipes, semicolons or commas 
    Returns (name, day, month, year, celebration_time).
    """
    payload = text.split(" ",1)[1] if " " in text else ""
    parts = [p.strip() for p in re.split(r"[|;,]", payload) if p.strip()]
    if len(parts) < 2:
        raise ParseError(
            "We need at least a name and a date.\n"
            "Example: add Anirudh| 05-03-2004| 09:00"
        )
    
    name = parts[0]
    day, month, year = parse_date(parts[1])
    celebration_time = parse_time(parts[2]) if len(parts) > 2 else default_time
    return name, day, month, year, celebration_time

def escape_html(text: str) -> str:
    return escape(text)