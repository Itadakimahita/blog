import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from redis.asyncio import from_url as redis_from_url


COMMENT_GROUP_PREFIX = "post_comments"
POST_PUBLICATION_CHANNEL = "posts_published"


def comment_group_name(slug: str) -> str:
    return f"{COMMENT_GROUP_PREFIX}_{slug}"


def serialize_comment(comment) -> dict:
    return {
        "comment_id": comment.id,
        "author": {
            "id": comment.author_id,
            "email": comment.author.email,
        },
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }


async def publish_comment_to_post_group(comment) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    await channel_layer.group_send(
        comment_group_name(comment.post.slug),
        {
            "type": "comment.message",
            "data": serialize_comment(comment),
        },
    )


def publish_comment_to_post_group_sync(comment) -> None:
    async_to_sync(publish_comment_to_post_group)(comment)


def serialize_post_publication(post) -> dict:
    return {
        "post_id": post.id,
        "title": post.title,
        "slug": post.slug,
        "author": {
            "id": post.author_id,
            "email": post.author.email,
        },
        "published_at": post.published_at.isoformat() if post.published_at else None,
    }


async def publish_post_publication(post) -> None:
    redis_client = redis_from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis_client.publish(
            POST_PUBLICATION_CHANNEL,
            json.dumps(serialize_post_publication(post)),
        )
    finally:
        await redis_client.aclose()


def publish_post_publication_sync(post) -> None:
    async_to_sync(publish_post_publication)(post)
