import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.blog.models import Post
from apps.notifications.services import comment_group_name


User = get_user_model()


class CommentConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        token = parse_qs(self.scope["query_string"].decode()).get("token", [None])[0]
        if not token:
            await self.close(code=4001)
            return

        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            self.user = await self._get_user(user_id)
        except (KeyError, TokenError, User.DoesNotExist):
            await self.close(code=4001)
            return

        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        exists = await self._post_exists(self.slug)
        if not exists:
            await self.close(code=4004)
            return

        self.group_name = comment_group_name(self.slug)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def comment_message(self, event: dict) -> None:
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def _get_user(self, user_id: int):
        return User.objects.get(pk=user_id, is_active=True)

    @database_sync_to_async
    def _post_exists(self, slug: str) -> bool:
        return Post.objects.filter(slug=slug).exists()
