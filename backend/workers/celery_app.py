from celery import Celery

from backend.config import get_settings

celery_app = Celery(
    "compliance_desk",
    broker=get_settings().redis_url or "memory://",
    backend=get_settings().redis_url or "cache+memory://",
    include=["backend.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=120,
    task_soft_time_limit=105,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
