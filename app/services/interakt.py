from typing import Tuple

import httpx

from app.core.config import settings


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
            "bodyValues": body_values,
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
