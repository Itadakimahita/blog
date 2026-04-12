from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.blog.enums.post_status import PostStatus
from apps.blog.models import Post
from apps.notifications.services import publish_post_publication_sync


@receiver(pre_save, sender=Post)
def remember_previous_post_state(sender, instance: Post, **kwargs) -> None:
    if instance.status == PostStatus.PUBLISHED and instance.published_at is None:
        instance.published_at = timezone.now()

    if not instance.pk:
        instance._previous_status = None
        return

    instance._previous_status = (
        Post.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    )


@receiver(post_save, sender=Post)
def publish_post_published_event(sender, instance: Post, created: bool, **kwargs) -> None:
    previous_status = getattr(instance, "_previous_status", None)
    became_published = instance.status == PostStatus.PUBLISHED and (
        created or previous_status != PostStatus.PUBLISHED
    )
    if became_published:
        publish_post_publication_sync(instance)
