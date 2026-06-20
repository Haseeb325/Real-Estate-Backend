from celery import shared_task
import logging
import requests
import os

logger = logging.getLogger(__name__)

def send_email_via_brevo(to_email, subject, html_content):
    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": os.environ.get("BREVO_API_KEY"),
                "Content-Type": "application/json",
            },
            json={
                "sender": {"name": "Real Estate App", "email": os.environ.get("BREVO_SMTP_USER")},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            }
        )
        response.raise_for_status()
        logger.info(f"Email sent to {to_email} via Brevo API")
    except Exception as exc:
        logger.error(f"Failed to send email to {to_email}: {exc}")
        raise exc

@shared_task(bind=True)
def send_otp_email(self, email, otp):
    send_email_via_brevo(
        email, "Your Verification OTP",
        f"Your OTP is <strong>{otp}</strong>. It will expire in 60 seconds."
    )

@shared_task(bind=True)
def send_reset_password_email(self, email, link):
    send_email_via_brevo(
        email, "Reset Your Password",
        f"Click the link to reset your password:<br><a href='{link}'>{link}</a>"
    )

@shared_task(bind=True)
def send_welcome_email(self, email, name):
    send_email_via_brevo(
        email, f"Welcome to our platform, {name}!",
        f"Hi {name},<br><br>Welcome to our platform! We are excited to have you on board."
    )