import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_logger

from app.config import settings

celery_app = Celery(
    "tradyon_outreach",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "sequence-processor": {
            "task": "app.tasks.sequence_processor.process_sequences",
            "schedule": crontab(minute="0"),  # every hour
        },
        "inbox-poller-morning": {
            "task": "app.tasks.inbox_poller.poll_inboxes",
            "schedule": crontab(hour="9", minute="0"),  # 9:00 AM UTC daily
        },
        "inbox-poller-evening": {
            "task": "app.tasks.inbox_poller.poll_inboxes",
            "schedule": crontab(hour="17", minute="0"),  # 5:00 PM UTC daily
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])


@after_setup_logger.connect
def setup_celery_logging(logger: logging.Logger, **kwargs):
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | celery.%(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for handler in logger.handlers:
        handler.setFormatter(formatter)
