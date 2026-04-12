import os

from celery import Celery
from celery.schedules import crontab


from settings.conf import ENV_ID


os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{ENV_ID}")


app = Celery("blog")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "publish-scheduled-posts-every-minute": {
        "task": "apps.blog.tasks.publish_scheduled_posts",
        "schedule": crontab(minute="*"),
    },
    "clear-expired-notifications-daily": {
        "task": "apps.notifications.tasks.clear_expired_notifications",
        "schedule": crontab(minute=0, hour=3),
    },
    "generate-daily-stats-midnight": {
        "task": "apps.blog.tasks.generate_daily_stats",
        "schedule": crontab(minute=0, hour=0),
    },
}
app.conf.timezone = "UTC"
