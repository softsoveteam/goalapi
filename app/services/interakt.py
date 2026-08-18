from typing import Tuple

import httpx

from app.core.config import settings

# Interakt / Meta template copy (Utility, language en). Recreate before deploy.
# Task URL is never in the body. Interakt button must be:
#   https://api.interakt.ai/cta?redirect={{1}}
# API sends buttonValues {{1}} as the full https task URL, e.g.
#   https://task.softsove.com/t/{public_id}
# Assign template name: teamtask
#
# teamtask — 6 body vars + View My Task button
# Hello {{1}},
# A new task has been assigned to you.
# Task: {{2}}
# Priority: {{3}}
# Details: {{4}}
# Deadline: {{5}}
# Time remaining: {{6}}
# Please review and complete this task on time.
#
# task_reminder — 3 body vars + button
# Hello {{1}},
# This is a reminder that the following task is still pending.
# Task: {{2}}
# Deadline: {{3}}
# Please complete it at the earliest.
#
# task_warning — 3 body vars + button
# Hello {{1}},
# Final reminder: the following task is still overdue.
# Task: {{2}}
# Deadline: {{3}}
# Please close this task immediately.
#
# daily_digest — 3 body vars, no button. Sent to each assignee's WhatsApp only.
# Daily task summary for {{1}}
# Completed today:
# {{2}}
# Still pending:
# {{3}}
#
# task_completed — 3 body vars, no button
# Task completed.
# Task: {{1}}
# Closed by: {{2}}
# Time taken: {{3}}


def split_phone(raw: str) -> Tuple[str, str]:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if digits.startswith("91") and len(digits) >= 12:
        return "+91", digits[2:]
    if len(digits) == 10:
        return "+91", digits
    if len(digits) > 10:
        return "+" + digits[:-10], digits[-10:]
    return "+91", digits


def send_template(phone: str, template_name: str, body_values, button_suffix: str = "") -> None:
    if not settings.interakt_api_key or not phone or not template_name:
        print("[interakt] skip send template={0} phone={1}".format(template_name, phone))
        return
    country, number = split_phone(phone)
    payload = {
        "countryCode": country,
        "phoneNumber": number,
        "callbackData": template_name,
        "type": "Template",
        "template": {
            "name": template_name,
            "languageCode": settings.interakt_language,
            "bodyValues": [str(value) if value else "-" for value in body_values],
        },
    }
    if button_suffix:
        payload["template"]["buttonValues"] = {"0": [button_suffix]}
    headers = {
        "Authorization": "Basic {0}".format(settings.interakt_api_key),
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=15) as client:
            res = client.post("https://api.interakt.ai/v1/public/message/", json=payload, headers=headers)
            if res.status_code >= 400:
                print("[interakt] failed {0}: {1}".format(res.status_code, res.text))
            else:
                print("[interakt] sent {0} to {1}{2}".format(template_name, country, number))
    except Exception as exc:
        print("[interakt] error: {0}".format(exc))
