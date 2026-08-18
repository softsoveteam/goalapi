import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_otp_email(to_email: str, code: str) -> None:
    subject = "Your SOFTSOVE login code"
    body = (
        "Your one-time login code is {0}.\n\n"
        "It expires in 10 minutes. If you did not request this, ignore this email."
    ).format(code)

    if not settings.smtp_host or not settings.smtp_from:
        print("[smtp] OTP for {0}: {1}".format(to_email, code))
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
