from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url


class Command(BaseCommand):
    """
    Async Redis listener for the 'comments' channel.

    Async is chosen here because pub/sub is a long-lived I/O stream; using sync code would block
    the thread and makes graceful cancellation/reconnect logic harder without threads.
    """

    help = "Subscribe to the Redis 'comments' channel and print incoming JSON events."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--channel", default="comments")
        parser.add_argument("--redis-url", default=None)
        parser.add_argument("--ping-interval", type=float, default=10.0)

    def handle(self, *args: tuple[Any, ...], **options: Dict[str, Any]) -> None:
        asyncio.run(self._run(options))

    async def _run(self, options: Dict[str, Any]) -> None:
        channel: str = str(options["channel"])
        redis_url: Optional[str] = options.get("redis_url") or getattr(settings, "REDIS_URL", None)
        ping_interval: float = float(options["ping_interval"])

        if not redis_url:
            self.stderr.write(self.style.ERROR("REDIS_URL is not configured."))
            return

        redis_client: Redis = redis_from_url(redis_url, decode_responses=False)
        pubsub = redis_client.pubsub()

        self.stdout.write(self.style.SUCCESS(f"Listening on Redis channel: {channel}"))

        try:
            await pubsub.subscribe(channel)
            last_ping = asyncio.get_event_loop().time()

            async for message in pubsub.listen():
                # redis-py pubsub delivers dict messages.
                if message.get("type") != "message":
                    continue

                raw_data = message.get("data")
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8", errors="replace")

                try:
                    parsed = json.loads(raw_data)
                    # Must contain at minimum: post_slug, author_id, body.
                    self.stdout.write(json.dumps(parsed, ensure_ascii=False))
                except (TypeError, json.JSONDecodeError):
                    self.stdout.write(str(raw_data))

                now = asyncio.get_event_loop().time()
                if now - last_ping >= ping_interval:
                    try:
                        await redis_client.ping()
                    except Exception:
                        self.stderr.write(self.style.ERROR("Redis ping failed; connection may be down."))
                    last_ping = now
        finally:
            try:
                await pubsub.close()
            except Exception:
                pass
            try:
                await redis_client.aclose()
            except Exception:
                pass
