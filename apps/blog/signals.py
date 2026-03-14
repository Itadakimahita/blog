from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.blog.cache import bump_published_posts_list_version
from apps.blog.models import Post


@receiver(post_save, sender=Post)
def _invalidate_posts_list_on_save(sender, instance: Post, **kwargs) -> None:
    bump_published_posts_list_version()


@receiver(post_delete, sender=Post)
def _invalidate_posts_list_on_delete(sender, instance: Post, **kwargs) -> None:
    bump_published_posts_list_version()

