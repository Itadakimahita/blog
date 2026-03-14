from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
from asgiref.sync import async_to_sync
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response as DRFResponse
from rest_framework.status import HTTP_200_OK, HTTP_502_BAD_GATEWAY
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.abstracts.serializers import ErrorDetailSerializer, StatsResponseSerializer
from apps.blog.models import Comments, Post
from apps.users.models import CustomUser


class StatsAPIView(APIView):
    """
    Stats endpoint that demonstrates concurrent I/O (two independent external HTTP calls).

    DRF's APIView dispatch is synchronous in this project, so we run an async coroutine via async_to_sync.
    If this were written as fully synchronous HTTP calls, total time would be the *sum* of both calls,
    instead of being bounded by the slower one.
    """

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        summary="Get blog stats + external data",
        description=(
            "Returns local blog statistics combined with external public data.\n\n"
            "Authentication: not required.\n"
            "Side effects: none.\n"
            "Language/timezone: response contains only data; any error messages are localized using the active request language.\n\n"
            "Concurrency: the exchange rates and current time are fetched concurrently using asyncio.gather "
            "so the total time does not exceed the slowest of the two calls."
        ),
        tags=["Stats"],
        responses={
            HTTP_200_OK: StatsResponseSerializer,
            HTTP_502_BAD_GATEWAY: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "200 Response Example",
                response_only=True,
                value={
                    "blog": {"total_posts": 42, "total_comments": 137, "total_users": 15},
                    "exchange_rates": {"KZT": 450.23, "RUB": 89.1, "EUR": 0.92},
                    "current_time": "2024-03-15T18:30:00+05:00",
                },
            ),
        ],
    )
    def get(self, request, *args, **kwargs) -> DRFResponse:
        exchange_url = "https://open.er-api.com/v6/latest/USD"
        time_url = "https://worldtimeapi.org/api/timezone/Asia/Almaty"

        async def _fetch_external() -> tuple[Dict[str, float], str]:
            # Async is chosen here to fetch two independent external resources concurrently.
            # Synchronous fetching would block on the first call before even starting the second.
            async with httpx.AsyncClient(timeout=5.0) as client:
                exchange_resp, time_resp = await asyncio.gather(
                    client.get(exchange_url),
                    client.get(time_url),
                )
                exchange_resp.raise_for_status()
                time_resp.raise_for_status()

            exchange_json: Dict[str, Any] = exchange_resp.json()
            time_json: Dict[str, Any] = time_resp.json()

            rates = (exchange_json.get("rates") or {})
            exchange_rates = {
                "KZT": float(rates["KZT"]),
                "RUB": float(rates["RUB"]),
                "EUR": float(rates["EUR"]),
            }
            current_time = str(time_json["datetime"])
            return exchange_rates, current_time

        try:
            exchange_rates, current_time = async_to_sync(_fetch_external)()
        except Exception:
            return DRFResponse(
                {"detail": _("Failed to fetch external data.")},
                status=HTTP_502_BAD_GATEWAY,
            )

        blog_counts = {
            "total_posts": int(Post.objects.count()),
            "total_comments": int(Comments.objects.count()),
            "total_users": int(CustomUser.objects.count()),
        }

        return DRFResponse(
            {"blog": blog_counts, "exchange_rates": exchange_rates, "current_time": current_time},
            status=HTTP_200_OK,
        )
