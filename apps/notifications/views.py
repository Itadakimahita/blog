import asyncio

from django.conf import settings
from django.http import StreamingHttpResponse
from redis.asyncio import from_url as redis_from_url
from rest_framework import generics, pagination, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import POST_PUBLICATION_CHANNEL


class NotificationPagination(pagination.PageNumberPagination):
    page_size = 20


class NotificationListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("comment__author", "comment__post")
            .order_by("-created_at")
        )


class NotificationCountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Polling is a good fit when the data is tiny and a few seconds of staleness is acceptable:
        # it keeps both the backend and client simple. The trade-off is repeated requests, which adds
        # latency and server load, so once freshness matters or the poll volume grows, switch to SSE
        # for one-way streams or WebSockets for fully interactive real-time features.
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": unread_count})


class NotificationReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({"marked_read": updated}, status=status.HTTP_200_OK)


async def post_publication_stream(request) -> StreamingHttpResponse:
    # SSE is a strong fit here because clients only need a one-way stream of newly published posts.
    # If the client also needed to send live messages back to the server or manage richer interactive
    # sessions, WebSockets would be the better choice.
    async def event_stream():
        redis_client = redis_from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(POST_PUBLICATION_CHANNEL)

        try:
            yield "retry: 5000\n\n"
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )
                if message is None:
                    yield ": keep-alive\n\n"
                    await asyncio.sleep(0)
                    continue

                yield f"data: {message['data']}\n\n"
        finally:
            await pubsub.unsubscribe(POST_PUBLICATION_CHANNEL)
            await pubsub.aclose()
            await redis_client.aclose()

    response: StreamingHttpResponse = StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
