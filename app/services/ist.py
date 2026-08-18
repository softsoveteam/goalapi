from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings

IST = ZoneInfo(settings.app_timezone or "Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def to_ist(value: Optional[datetime]) -> Optional[datetime]:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(IST)


def as_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_hhmm(value: str) -> tuple[int, int]:
    parts = (value or "09:00").split(":")
    hour = max(0, min(23, int(parts[0])))
    minute = max(0, min(59, int(parts[1] if len(parts) > 1 else 0)))
    return hour, minute


def combine_ist(day, send_time: str) -> datetime:
    hour, minute = parse_hhmm(send_time)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST)


def add_one_month(value: datetime) -> datetime:
    year, month = value.year, value.month + 1
    if month > 12:
        year += 1
        month = 1
    last = monthrange(year, month)[1]
    day = min(value.day, last)
    return value.replace(year=year, month=month, day=day)


def compute_next_run(
    interval: str,
    send_time: str,
    weekday: Optional[int] = None,
    day_of_month: Optional[int] = None,
    after: Optional[datetime] = None,
) -> datetime:
    now = to_ist(after) if after else now_ist()
    today = now.date()
    hour, minute = parse_hhmm(send_time)

    if interval == "weekly":
        target_weekday = 0 if weekday is None else int(weekday)
        days_ahead = (target_weekday - now.weekday()) % 7
        candidate = combine_ist(today + timedelta(days=days_ahead), send_time)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    if interval == "monthly":
        wanted = day_of_month or today.day
        last = monthrange(today.year, today.month)[1]
        candidate = datetime(today.year, today.month, min(wanted, last), hour, minute, tzinfo=IST)
        if candidate <= now:
            nxt = add_one_month(candidate.replace(day=1))
            last_next = monthrange(nxt.year, nxt.month)[1]
            candidate = nxt.replace(day=min(wanted, last_next), hour=hour, minute=minute)
        return candidate

    candidate = combine_ist(today, send_time)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def end_of_ist_day(day) -> datetime:
    return datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=IST)


def period_window(last_start, cycle_days: int, today):
    cycle = max(21, min(45, int(cycle_days or 28)))
    expected = last_start + timedelta(days=cycle)
    guard = 0
    while expected + timedelta(days=4) < today and guard < 36:
        expected = expected + timedelta(days=cycle)
        guard += 1
    start = expected - timedelta(days=2)
    end = expected + timedelta(days=4)
    if today > end:
        expected = expected + timedelta(days=cycle)
        start = expected - timedelta(days=2)
        end = expected + timedelta(days=4)
    return start, end, expected


def compute_period_next_run(last_start, cycle_days: int, send_time: str, after: Optional[datetime] = None) -> datetime:
    now = to_ist(after) if after else now_ist()
    today = now.date()
    start, end, _expected = period_window(last_start, cycle_days, today)
    cursor = today
    if cursor < start:
        return combine_ist(start, send_time)
    while cursor <= end:
        candidate = combine_ist(cursor, send_time)
        if candidate > now:
            return candidate
        cursor = cursor + timedelta(days=1)
    start2, _end2, _ = period_window(last_start, cycle_days, end + timedelta(days=1))
    return combine_ist(start2, send_time)
