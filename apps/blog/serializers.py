from typing import Any, Dict, Optional
import logging

# Django modules
from django.utils import formats, timezone
from django.utils.translation import get_language

# Django REST Framework modules
from rest_framework.serializers import ModelSerializer, SerializerMethodField, CharField, ValidationError

# Project modules
from apps.blog.models import Post, Comments, Tags, Category
from apps.blog.enums.post_status import PostStatus
from apps.users.models import CustomUser


logger = logging.getLogger("blog")


class PostDetailSerializer(ModelSerializer):
    """
    Serializer for the Post model, which includes the following fields:
    - `id`: The unique identifier of the post.
    - `title`: The title of the post.
    - `content`: The content of the post.
    - `author`: The username of the author of the post.
    - `created_at`: The date and time when the post was created.
    """
    author = CharField(source="author.email", read_only=True)
    created_at_display = SerializerMethodField()
    updated_at_display = SerializerMethodField()
    category = SerializerMethodField()
    
    class Meta:
        """Meta class for PostDetailSerializer to specify the model and fields to be serialized."""
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "body",
            "status",
            "author",
            "category",
            "published_at",
            "publish_at",
            "created_at",
            "updated_at",
            "created_at_display",
            "updated_at_display",
        ]

    def _format_dt(self, dt) -> str:
        dt_local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
        return formats.date_format(dt_local, format="DATETIME_FORMAT", use_l10n=True)

    def get_created_at_display(self, obj: Post) -> str:
        return self._format_dt(obj.created_at)

    def get_updated_at_display(self, obj: Post) -> str:
        return self._format_dt(obj.updated_at)

    def get_category(self, obj: Post) -> Optional[Dict[str, str]]:
        if not obj.category_id or not obj.category:
            return None
        lang = get_language()
        return {"slug": obj.category.slug, "name": obj.category.name_for_language(lang)}
    

class PostCreateSerializer(ModelSerializer):
    """
    Serializer for creating a new post, which includes the following fields:
    - `title`: The title of the post.
    - `content`: The content of the post.
    - `author`: The ID of the author of the post.
    """
    
    class Meta:
        """Meta class for PostCreateSerializer to specify the model and fields to be serialized."""
        model = Post
        fields = ['title', 'slug', 'body', 'status', 'publish_at', 'author']
        extra_kwargs = {
            "author": {"read_only": True},
        }

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        status = attrs.get("status", getattr(self.instance, "status", PostStatus.DRAFT))
        publish_at = attrs.get("publish_at", getattr(self.instance, "publish_at", None))
        if status == PostStatus.SCHEDULED and publish_at is None:
            raise ValidationError({"publish_at": "This field is required when status is scheduled."})
        return attrs
    
    def create(self, validated_data: Dict[str, Any]) -> Post:
        """Create a new post instance."""
        author = validated_data.get("author")
        author_email = getattr(author, "email", None)
        logger.info("Post creation attempt by author: %s", author_email)
        try:
            post = Post.objects.create(**validated_data)
            logger.info("Post created: %s", post.slug)
            return post
        except Exception:
            logger.exception("Post creation failed for author: %s", author_email)
            raise

    def update(self, instance: Post, validated_data: Dict[str, Any]) -> Post:
        """Update an existing post instance."""
        logger.info("Post update attempt: %s", instance.slug)
        try:
            post = super().update(instance, validated_data)
            logger.info("Post updated: %s", post.slug)
            return post
        except Exception:
            logger.exception("Post update failed: %s", instance.slug)
            raise
        
class CommentDetailSerializer(ModelSerializer):
    """
    Serializer for the Comment model, which includes the following fields:
    - `id`: The unique identifier of the comment.
    - `post`: The ID of the post that the comment belongs to.
    - `author`: The username of the author of the comment.
    - `body`: The content of the comment.
    - `created_at`: The date and time when the comment was created.
    """
    author = CharField(source="author.email", read_only=True)
    
    class Meta:
        """Meta class for CommentSerializer to specify the model and fields to be serialized."""
        model = Comments
        fields = ['id', 'post', 'author', 'body', 'created_at']
        

class CommentCreateSerializer(ModelSerializer):
    """
    Serializer for creating a new comment, which includes the following fields:
    - `post`: The ID of the post that the comment belongs to.
    - `author`: The ID of the author of the comment.
    - `body`: The content of the comment.
    """

    # Backward-compatible alias: accept `content` and map to `body`.
    content = CharField(write_only=True, required=False)
    
    class Meta:
        """Meta class for CommentCreateSerializer to specify the model and fields to be serialized."""
        model = Comments
        fields = ['post', 'author', 'body', 'content']
        extra_kwargs = {
            "post": {"read_only": True},
            "author": {"read_only": True},
        }

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if not attrs.get("body") and attrs.get("content"):
            attrs["body"] = attrs["content"]
        return attrs
    
    def create(self, validated_data: Dict[str, Any]) -> Comments:
        """Create a new comment instance."""
        validated_data.pop("content", None)
        post = validated_data.get("post")
        logger.debug("Comment creation attempt for post_id=%s", getattr(post, "id", None))
        try:
            comment = Comments.objects.create(**validated_data)
            logger.info("Comment created for post_id=%s", comment.post_id)
            return comment
        except Exception:
            logger.exception("Comment creation failed for post_id=%s", getattr(post, "id", None))
            raise
    
