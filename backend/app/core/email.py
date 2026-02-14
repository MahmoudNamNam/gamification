"""
Send email via SMTP (e.g. Gmail). Used for OTP delivery.
Credentials from settings; if SMTP_HOST is empty, no email is sent.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings


def is_smtp_configured() -> bool:
    return bool(
        settings.SMTP_HOST and
        settings.SMTP_USERNAME and
        settings.SMTP_PASSWORD and
        settings.SMTP_FROM_EMAIL
    )


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> None:
    """
    Send an email via SMTP. Raises on failure.
    No-op if SMTP is not configured (SMTP_HOST empty).
    """
    if not is_smtp_configured():
        return
    from_email = settings.SMTP_FROM_EMAIL
    from_name = settings.SMTP_FROM_NAME or "Khaleeji"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(from_email, [to_email], msg.as_string())


def send_otp_email(to_email: str, otp: str, purpose: str) -> None:
    """Send OTP email. No-op if SMTP not configured."""
    purpose_labels = {
        "register": "تسجيل حساب جديد",
        "login": "تسجيل الدخول",
        "forgot_password": "استعادة كلمة المرور",
    }
    label = purpose_labels.get(purpose, purpose)
    subject = f"رمز التحقق (OTP) - {label}"
    body_text = f"رمز التحقق الخاص بك هو: {otp}\n\nصالح لمدة 10 دقائق.\n\nإذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة."
    body_html = (
        f"<p>رمز التحقق الخاص بك هو: <strong>{otp}</strong></p>"
        f"<p>صالح لمدة 10 دقائق.</p>"
        "<p>إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.</p>"
    )
    send_email(to_email, subject, body_text, body_html)
