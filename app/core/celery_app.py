from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("users_api", broker=settings.redis_url)
celery_app.conf.timezone = "UTC"
# Beat tasks are fire-and-forget; don't write results to Redis.
celery_app.conf.task_ignore_result = True

celery_app.conf.beat_schedule = {
    "purge-unverified-users": {
        "task": "app.tasks.delete_expired_unverified_users",
        # Hourly is granular enough for a 2-day TTL.
        "schedule": crontab(minute=0),
    },
}

celery_app.autodiscover_tasks(["app"])
