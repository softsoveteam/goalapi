from app.core.config import settings
from app.db.models import Task
from app.services import interakt
from app.services.timefmt import format_deadline, format_remaining


def clip(value: str, limit: int = 400) -> str:
    text = (value or "").replace("\n", " ").strip() or "-"
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def task_url(task: Task) -> str:
    return "{0}/t/{1}".format(settings.app_public_url.rstrip("/"), task.public_id)


def priority_label(value: str) -> str:
    return (value or "normal").replace("_", " ").title()


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
            task_url(task),
        ],
        button_suffix=task.public_id,
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
            task_url(task),
        ],
        button_suffix=task.public_id,
    )
