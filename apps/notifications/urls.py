from django.urls import path

from apps.notifications.views import (
    NotificationCountAPIView,
    NotificationListAPIView,
    NotificationReadAPIView,
)


urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="notifications-list"),
    path("count/", NotificationCountAPIView.as_view(), name="notifications-count"),
    path("read/", NotificationReadAPIView.as_view(), name="notifications-read"),
]
