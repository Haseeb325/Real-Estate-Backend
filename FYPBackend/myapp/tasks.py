from celery import shared_task
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_email_via_resend(to_email, subject, html_content):
    try:
        # Since we configured ANYMAIL and EMAIL_BACKEND in settings.py,
        # this send_mail call will automatically be sent using Resend!
        send_mail(
            subject=subject,
            message="",  # Plain text body
            from_email=settings.DEFAULT_FROM_EMAIL,  # "onboarding@resend.dev"
            recipient_list=[to_email],
            html_message=html_content,
            fail_silently=False,
        )
        logger.info(f"Email sent to {to_email} via Resend")
    except Exception as exc:
        logger.error(f"Failed to send email to {to_email}: {exc}")
        raise exc

@shared_task(bind=True)
def send_otp_email(self, email, otp):
    send_email_via_resend(
        email, "Your Verification OTP",
        f"Your OTP is <strong>{otp}</strong>. It will expire in 60 seconds."
    )

@shared_task(bind=True)
def send_reset_password_email(self, email, link):
    send_email_via_resend(
        email, "Reset Your Password",
        f"Click the link to reset your password:<br><a href='{link}'>{link}</a>"
    )

@shared_task(bind=True)
def send_welcome_email(self, email, name):
    send_email_via_resend(
        email, f"Welcome to our platform, {name}!",
        f"Hi {name},<br><br>Welcome to our platform! We are excited to have you on board."
    )