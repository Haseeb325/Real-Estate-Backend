from celery import shared_task
from django.core.mail import send_mail
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def send_otp_email(self, email, otp):
    try:
        send_mail(
            subject="Your Verification OTP",
            message=f"Your OTP is {otp}. It will expire in 60 seconds.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f"Failed to send OTP email to {email}: {exc}")


@shared_task(bind=True)
def send_reset_password_email(self, email, link):
    try:
        send_mail(
            subject="Reset Your Password",
            message=f"Click the link to reset your password:\n{link}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f"Failed to send reset password email to {email}: {exc}")

@shared_task(bind=True)
def send_welcome_email(self, email, name):
    try:
        send_mail(
            subject=f"Welcome to our platform, {name}!",
            message=f"Hi {name},\n\nWelcome to our platform! We are excited to have you on board.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f"Failed to send welcome email to {email}: {exc}")
