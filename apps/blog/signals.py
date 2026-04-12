from __future__ import annotations

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.blog.models import Post
from apps.blog.tasks import invalidate_posts_cache


@receiver(post_save, sender=Post)
def _invalidate_posts_list_on_save(sender, instance: Post, **kwargs) -> None:
    transaction.on_commit(lambda: invalidate_posts_cache.delay())


@receiver(post_delete, sender=Post)
def _invalidate_posts_list_on_delete(sender, instance: Post, **kwargs) -> None:
    transaction.on_commit(lambda: invalidate_posts_cache.delay())

