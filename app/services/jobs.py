import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.models import JobRun, RecurringRule, Task, TaskItem
from app.db.session import SessionLocal
from app.services.ist import as_utc_naive, compute_next_run, end_of_ist_day, now_ist, to_ist
from app.services.notify import clip, send_task_assigned, send_task_reminder
from app.services import interakt


def _claim_job(db: Session, name: str) -> bool:
    today = now_ist().date()
    existing = db.query(JobRun).filter(JobRun.job_name == name, JobRun.run_date == today).first()
    if existing:
        return False
    db.add(JobRun(job_name=name, run_date=today))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _open_tasks(db: Session):
    return (
        db.query(Task)
        .options(joinedload(Task.assignee))
        .filter(Task.is_done.is_(False), Task.deadline.isnot(None), Task.is_archived.is_(False))
        .all()
    )


def run_reminders() -> dict:
    db = SessionLocal()
    sent_reminder = 0
    sent_warning = 0
    try:
        if not _claim_job(db, "reminders"):
            return {"ok": True, "skipped": True, "job": "reminders"}
        today = now_ist().date()
        now = datetime.now(timezone.utc)
        for task in _open_tasks(db):
            deadline_ist = to_ist(task.deadline)
            if not deadline_ist:
                continue
            days_overdue = (today - deadline_ist.date()).days
            if days_overdue >= 2 and not task.warned_at:
                send_task_reminder(task, settings.interakt_template_warning)
                task.warned_at = now
                if not task.reminded_at:
                    task.reminded_at = now
                sent_warning += 1
            elif days_overdue >= 1 and not task.reminded_at:
                send_task_reminder(task, settings.interakt_template_reminder)
                task.reminded_at = now
                sent_reminder += 1
        db.commit()
        return {
            "ok": True,
            "job": "reminders",
            "reminders": sent_reminder,
            "warnings": sent_warning,
        }
    finally:
        db.close()


def _digest_lines(tasks, include_assignee: bool = True, limit: int = 12) -> str:
    if not tasks:
        return "None"
    lines = []
    extra = max(0, len(tasks) - limit)
    for task in tasks[:limit]:
        name = task.assignee.name if include_assignee and task.assignee else ""
        if name:
            lines.append("- {0} ({1})".format(task.title, name))
        else:
            lines.append("- {0}".format(task.title))
    if extra:
        lines.append("...and {0} more".format(extra))
    return clip("\n".join(lines), 900)


def run_digest() -> dict:
    db = SessionLocal()
    try:
        if not _claim_job(db, "digest"):
            return {"ok": True, "skipped": True, "job": "digest"}
        today = now_ist().date()
        start = as_utc_naive(now_ist().replace(hour=0, minute=0, second=0, microsecond=0))
        end = as_utc_naive(end_of_ist_day(today))
        q = db.query(Task).options(joinedload(Task.assignee)).filter(Task.is_archived.is_(False))
        completed = (
            q.filter(Task.is_done.is_(True), Task.closed_at >= start, Task.closed_at <= end)
            .order_by(Task.closed_at.desc())
            .all()
        )
        pending = q.filter(Task.is_done.is_(False)).order_by(Task.id.desc()).all()
        date_label = now_ist().strftime("%d %b %Y")
        if settings.admin_whatsapp:
            interakt.send_template(
                settings.admin_whatsapp,
                settings.interakt_template_digest,
                [
                    date_label,
                    _digest_lines(completed),
                    _digest_lines(pending),
                ],
            )
        return {
            "ok": True,
            "job": "digest",
            "completed": len(completed),
            "pending": len(pending),
        }
    finally:
        db.close()


def _spawn_from_rule(db: Session, rule: RecurringRule) -> Task:
    run_day = now_ist().date()
    deadline = as_utc_naive(end_of_ist_day(run_day))
    try:
        titles = json.loads(rule.checklist_json or "[]")
    except json.JSONDecodeError:
        titles = []
    if not isinstance(titles, list):
        titles = []
    task = Task(
        title=rule.title,
        description=rule.description,
        assigned_to=rule.assigned_to,
        created_by=rule.created_by,
        priority=rule.priority or "normal",
        deadline=deadline,
        is_done=False,
        recurring_rule_id=rule.id,
    )
    db.add(task)
    db.flush()
    for index, title in enumerate(titles):
        text = str(title).strip()
        if not text:
            continue
        db.add(TaskItem(task_id=task.id, title=text[:300], sort_order=index, is_done=False))
    return task


def run_recurring() -> dict:
    db = SessionLocal()
    created = 0
    try:
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        rules = (
            db.query(RecurringRule)
            .options(joinedload(RecurringRule.assignee))
            .filter(RecurringRule.is_active.is_(True), RecurringRule.next_run_at <= now_naive)
            .all()
        )
        for rule in rules:
            rule.next_run_at = as_utc_naive(
                compute_next_run(
                    rule.interval,
                    rule.send_time,
                    rule.weekday,
                    rule.day_of_month,
                    after=now_ist(),
                )
            )
            db.commit()
            task = _spawn_from_rule(db, rule)
            db.commit()
            loaded = (
                db.query(Task)
                .options(joinedload(Task.assignee), selectinload(Task.items))
                .filter(Task.id == task.id)
                .first()
            )
            send_task_assigned(loaded)
            created += 1
        return {"ok": True, "job": "recurring", "created": created}
    finally:
        db.close()
