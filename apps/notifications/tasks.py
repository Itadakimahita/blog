from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.blog.models import Comments
from apps.notifications.models import Notification
from apps.notifications.services import publish_comment_to_post_group_sync


logger = logging.getLogger("blog")


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_new_comment(comment_id: int) -> None:
    """Process side effects of a new comment being created."""
    comment = Comments.objects.select_related("author", "post", "post__author").get(pk=comment_id)

    if comment.post.author_id != comment.author_id:
        Notification.objects.get_or_create(
            recipient=comment.post.author,
            comment=comment,
        )

    publish_comment_to_post_group_sync(comment)
    logger.info("Processed new comment side effects for comment_id=%s", comment_id)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def clear_expired_notifications() -> int:
    """Delete notifications older than 30 days and return the count of deleted notifications."""
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Cleared %s expired notifications", deleted_count)
    return deleted_count
