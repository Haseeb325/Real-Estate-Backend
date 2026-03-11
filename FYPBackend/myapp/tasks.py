from celery import shared_task
import logging
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

def send_email_via_sendgrid(to_email, subject, content):
    try:
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=content,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status: {response.status_code}")
    except Exception as exc:
        logger.error(f"Failed to send email to {to_email}: {exc}")
        raise exc

@shared_task(bind=True)
def send_otp_email(self, email, otp):
    send_email_via_sendgrid(
        email, "Your Verification OTP",
        f"Your OTP is <strong>{otp}</strong>. It will expire in 60 seconds."
    )

@shared_task(bind=True)
def send_reset_password_email(self, email, link):
    send_email_via_sendgrid(
        email, "Reset Your Password",
        f"Click the link to reset your password:<br><a href='{link}'>{link}</a>"
    )

@shared_task(bind=True)
def send_welcome_email(self, email, name):
    send_email_via_sendgrid(
        email, f"Welcome to our platform, {name}!",
        f"Hi {name},<br><br>Welcome to our platform! We are excited to have you on board."
    )