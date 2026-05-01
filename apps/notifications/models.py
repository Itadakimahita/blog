from django.db import models

from apps.abstracts.models import AbstractBaseModel
from apps.blog.models import Comments
from apps.users.models import CustomUser


class Notification(AbstractBaseModel):
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    comment = models.ForeignKey(
        Comments,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "comment"],
                name="unique_notification_per_recipient_comment",
            ),
        ]

    def __str__(self) -> str:
        return f"Notification(recipient={self.recipient_id}, comment={self.comment_id})"
