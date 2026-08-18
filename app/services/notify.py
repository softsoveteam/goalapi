from app.core.config import settings
from app.db.models import Task
from app.services import interakt
from app.services.timefmt import format_deadline, format_remaining


def clip(value: str, limit: int = 400) -> str:
    text = (value or "").replace("\n", " ").strip() or "-"
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def priority_label(value: str) -> str:
    return (value or "normal").replace("_", " ").title()


def task_button_url(task: Task) -> str:
    """Full https URL for Interakt CTA: https://api.interakt.ai/cta?redirect={{1}}"""
    base = (settings.app_public_url or "").rstrip("/")
    if base.startswith("http://"):
        base = "https://" + base[len("http://") :]
    elif not base.startswith("https://"):
        base = "https://{0}".format(base.lstrip("/"))
    return "{0}/t/{1}".format(base, task.public_id)


def send_task_assigned(task: Task) -> None:
    assignee = task.assignee
    if not assignee or not assignee.phone:
        print("[notify] skip assign, missing phone for task {0}".format(task.id))
        return
    interakt.send_template(
        assignee.phone,
        settings.interakt_template_task,
        [
            assignee.name,
            task.title,
            priority_label(task.priority),
            clip(task.description or "No description"),
            format_deadline(task.deadline),
            format_remaining(task.deadline),
        ],
        button_suffix=task_button_url(task),
    )


def send_care_note(phone: str, name: str, message: str, niche: str = "take_care", send_time: str = "") -> None:
    from app.services.care_messages import NICHE_LABELS

    first = (name or "there").split()[0]
    kind = NICHE_LABELS.get(niche, "Reminder")
    when = (send_time or "scheduled time") + " IST"
    interakt.send_template(
        phone,
        settings.interakt_template_care,
        [first, kind, when, clip(message, 400)],
    )


def send_task_reminder(task: Task, template_name: str) -> None:
    assignee = task.assignee
    if not assignee or not assignee.phone:
        return
    interakt.send_template(
        assignee.phone,
        template_name,
        [
            assignee.name,
            task.title,
            format_deadline(task.deadline),
        ],
        button_suffix=task_button_url(task),
    )
