import smtplib
from email.message import EmailMessage

from app.core.config import settings


def _app_password(raw: str) -> str:
    return (raw or "").replace(" ", "").strip()


def send_otp_email(to_email: str, code: str) -> None:
    subject = "Your SOFTSOVE login code"
    body = (
        "Your one-time login code is {0}.\n\n"
        "It expires in 10 minutes. If you did not request this, ignore this email."
    ).format(code)

    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    password = _app_password(settings.smtp_password)
    from_addr = (settings.smtp_from or user).strip()

    if not host or not user or not password or not from_addr:
        print("[smtp] OTP for {0}: {1}".format(to_email, code))
        raise RuntimeError(
            "Gmail SMTP is not configured. Set SMTP_USER and SMTP_PASSWORD (Google App Password) in .env"
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "SOFTSOVE <{0}>".format(from_addr)
    message["To"] = to_email
    message.set_content(body)

    port = settings.smtp_port or 587
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                smtp.login(user, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(user, password)
                smtp.send_message(message)
        print("[smtp] OTP sent to {0}".format(to_email))
    except Exception as exc:
        print("[smtp] failed to send OTP to {0}: {1}".format(to_email, exc))
        raise
