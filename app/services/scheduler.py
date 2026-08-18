from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.services import jobs

_scheduler = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    tz = ZoneInfo(settings.app_timezone or "Asia/Kolkata")
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        jobs.run_reminders,
        CronTrigger(hour=8, minute=45, timezone=tz),
        id="reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        jobs.run_digest,
        CronTrigger(hour=19, minute=0, timezone=tz),
        id="digest",
        replace_existing=True,
    )
    scheduler.add_job(
        jobs.run_recurring,
        IntervalTrigger(seconds=60),
        id="recurring",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    print("[scheduler] started IST 08:45 reminders, 19:00 digest, recurring every 60s")
