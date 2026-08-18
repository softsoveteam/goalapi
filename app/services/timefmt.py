from datetime import datetime, timezone
from typing import Optional


def format_remaining(deadline: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not deadline:
        return "No deadline"
    now = now or datetime.now(timezone.utc)
    target = deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    diff = int((target - current).total_seconds())
    if diff <= 0:
        return "Overdue"
    days, rem = divmod(diff, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return "{0}d {1:02d}:{2:02d}".format(days, hours, minutes)


def format_duration(start: datetime, end: datetime) -> str:
    start_aware = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
    end_aware = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
    diff = max(0, int((end_aware - start_aware).total_seconds()))
    days, rem = divmod(diff, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return "{0}d {1:02d}:{2:02d}".format(days, hours, minutes)


def format_deadline(deadline: Optional[datetime]) -> str:
    if not deadline:
        return "No deadline"
    target = deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)
    return target.strftime("%d %b %Y, %I:%M %p UTC")
