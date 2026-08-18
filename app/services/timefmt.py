from datetime import datetime, timezone
from typing import Optional

from app.services.ist import to_ist


def format_remaining(deadline: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not deadline:
        return "No deadline"
    target = to_ist(deadline)
    current = to_ist(now) if now else to_ist(datetime.now(timezone.utc))
    if target is None or current is None:
        return "No deadline"
    diff = int((target - current).total_seconds())
    if diff <= 0:
        return "Overdue"
    days, rem = divmod(diff, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return "{0}d {1:02d}:{2:02d}".format(days, hours, minutes)


def format_duration(start: datetime, end: datetime) -> str:
    start_aware = to_ist(start)
    end_aware = to_ist(end)
    diff = max(0, int((end_aware - start_aware).total_seconds()))
    days, rem = divmod(diff, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return "{0}d {1:02d}:{2:02d}".format(days, hours, minutes)


def format_deadline(deadline: Optional[datetime]) -> str:
    target = to_ist(deadline)
    if not target:
        return "No deadline"
    return target.strftime("%d %b %Y, %I:%M %p IST")
