from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "comment", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("recipient__email", "comment__body")
