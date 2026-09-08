"""
    ---> Domain Models and Reminder Time Maths <--- 
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

## Reminder Types/Kinds which we are persisting in the sent_reminders table <000>
KIND_DAY_BEFORE = "day_before"
KIND_HALF_HOUR = "half_hour"

@dataclass
class Birthday:
    id: int
    chat_id: int
    name: str
    day: int
    month: int
    year: int | None                        # Optional for showing us the age <00-00> 
    celebration_time: str                   # "HH:MM"
    note: str | None = None

    # ------- helpers -------

    @property
    def celebration_t(self) -> time:
        hh, mm = self.celebration_time.split(":")
        return time(int(hh),int(mm))
        
    def date_in_year(self, year: int) -> date:
        day = self.day
    
        if self.month == 2 and self.day == 29 and not calendar.isleap(year):
            day = 28
        
        return date(year, self.month, day)
        
    def occurrence(self, year: int, tz: ZoneInfo) -> datetime:
        return datetime.combine(self.date_in_year(year), self.celebration_t, tzinfo=tz)
    
    def next_occurrence(self, now: datetime, tz: ZoneInfo) -> datetime:
        occ = self.occurrence(now.year, tz)
        if occ < now:
            occ = self.occurrence(now.year+1,tz)
        return occ
    
    def age_turning(self, year:int) -> int | None:
        return None if self.year is None else year - self.year
    
    def days_until(self, now: datetime, tz: ZoneInfo) -> int:
        return (self.next_occurrence(now, tz).date() - now.date()).days
    
    def pretty(self, now: datetime, tz: ZoneInfo) -> str:
        occ = self.next_occurrence(now, tz)
        age = self.age_turning(occ.year)
        age_txt = f"(turns {age})" if age is not None else ""
        days = self.days_until(now, tz)
        when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
        return (f"#{self.id} . <b>{self.name}</b>{age_txt}\n"
                f"{occ.strftime('%d %b')} at {self.celebration_time} - {when}"
                )
    
@dataclass(frozen=True)
class DueReminder:
    birthday: Birthday
    kind: str
    year: int                   # the year of the birthday occurence this remidner belongs to <0---0>
    fire_at: datetime

def reminder_times(bd: Birthday, occurrence: datetime) -> dict[str,datetime]:
    """
        !---! TIME TWO REMINDER MOMENTS FOR A SINGLE BIRTHDAY OCCURRENCE !---! 
    """
    return {
        KIND_DAY_BEFORE: occurrence - timedelta(days=1),
        KIND_HALF_HOUR: occurrence - timedelta(minutes=30),
    }
    