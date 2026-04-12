from __future__ import annotations

import logging

from celery import shared_task

from apps.users.emails import send_welcome_email as send_welcome_email_message
from apps.users.models import CustomUser

logger = logging.getLogger("users")


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email(user_id: int, language: str) -> None:
    """Send a welcome email to the user with the given ID and language."""
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return
    send_welcome_email_message(user=user, language=language)
    logger.info("Welcome email task completed for user_id=%s", user_id)



