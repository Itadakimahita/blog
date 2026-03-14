from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import override

from apps.users.models import CustomUser

logger = logging.getLogger("users")


def send_welcome_email(*, user: CustomUser, language: str) -> None:
    """
    Send a welcome email rendered from templates.

    The email language is explicitly controlled by `language`, independent of the
    currently active request language.
    """
    recipient = user.email
    if not recipient:
        return

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    context = {"user": user}

    with override(language):
        subject = render_to_string("emails/welcome/subject.txt", context).strip()
        body = render_to_string("emails/welcome/body.txt", context)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info("Welcome email sent to %s", recipient)
    except Exception:
        logger.exception("Failed to send welcome email to %s", recipient)
