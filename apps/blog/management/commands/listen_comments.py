import json
from typing import Any, Dict

from django.core.management.base import BaseCommand
from django_redis import get_redis_connection


class Command(BaseCommand):
    """A Django management command that listens to the Redis 'comments' channel and prints incoming events."""
    help = "Subscribe to the Redis 'comments' channel and print incoming events."

    def handle(self, *args: tuple[Any, ...], **options: Dict[str, Any]) -> None:
        """Start listening to the Redis 'comments' channel and print incoming events."""
        redis_client = get_redis_connection("default")
        pubsub = redis_client.pubsub()
        pubsub.subscribe("comments")
        self.stdout.write(self.style.SUCCESS("Listening on Redis channel: comments"))

        for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            raw_data = message.get("data")
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8", errors="replace")

            try:
                parsed = json.loads(raw_data)
                self.stdout.write(json.dumps(parsed, ensure_ascii=True))
            except (TypeError, json.JSONDecodeError):
                self.stdout.write(str(raw_data))
