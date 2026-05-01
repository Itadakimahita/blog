from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    comment_id = serializers.IntegerField(source="comment_id", read_only=True)
    comment_body = serializers.CharField(source="comment.body", read_only=True)
    post = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "comment_id",
            "comment_body",
            "author",
            "post",
            "is_read",
            "created_at",
        ]

    def get_post(self, obj: Notification) -> dict:
        return {
            "id": obj.comment.post_id,
            "slug": obj.comment.post.slug,
            "title": obj.comment.post.title,
        }

    def get_author(self, obj: Notification) -> dict:
        return {
            "id": obj.comment.author_id,
            "email": obj.comment.author.email,
        }
