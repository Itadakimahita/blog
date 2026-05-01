from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import QuerySet
from django.utils import timezone

from apps.blog.cache import bump_published_posts_list_version
from apps.blog.enums.post_status import PostStatus
from apps.blog.models import Comments, Post
from apps.users.models import CustomUser


logger = logging.getLogger("blog")


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def invalidate_posts_cache() -> int:
    # Cache invalidation is infrastructure-bound work; retries help when Redis has a brief outage
    # so post create/update/delete requests do not need to synchronously absorb that failure.
    version = bump_published_posts_list_version()
    logger.info("Published posts cache invalidated. version=%s", version)
    return version


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def publish_scheduled_posts() -> int:
    # Scheduled publishing depends on the database and the beat/worker pipeline; retries prevent a
    # transient failure at one minute boundary from leaving ready-to-publish posts stuck in limbo.
    now = timezone.now()
    scheduled_posts: QuerySet[Post] = Post.objects.filter(
        status=PostStatus.SCHEDULED,
        publish_at__isnull=False,
        publish_at__lte=now,
    ).select_related("author")

    published_count = 0
    for post in scheduled_posts:
        post.status = PostStatus.PUBLISHED
        post.published_at = post.publish_at or now
        post.save(update_fields=["status", "published_at", "publish_at", "updated_at"])
        published_count += 1

    if published_count:
        logger.info("Published %s scheduled posts", published_count)
    return published_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_daily_stats() -> dict[str, int]:
    # Reporting tasks often touch multiple database tables and can fail during transient DB hiccups;
    # retries improve the odds that daily operational stats are still recorded without manual reruns.
    since = timezone.now() - timedelta(days=1)
    stats = {
        "posts": Post.objects.filter(created_at__gte=since).count(),
        "comments": Comments.objects.filter(created_at__gte=since).count(),
        "users": CustomUser.objects.filter(date_joined__gte=since).count(),
    }
    logger.info(
        "Daily stats for last 24h: posts=%s comments=%s users=%s",
        stats["posts"],
        stats["comments"],
        stats["users"],
    )
    return stats
