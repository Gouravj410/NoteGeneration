import os
import redis
from celery import Celery
from app.core.config import settings

# Detect if Redis is running locally
redis_available = False
if settings.REDIS_URL:
    try:
        # Dry-run connection ping to Redis
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        r.ping()
        redis_available = True
    except Exception:
        pass

if redis_available:
    celery_app = Celery(
        "studyforge_tasks",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["app.tasks.document_tasks"]
    )
else:
    print("[Celery Info] Redis server not found. Falling back to synchronous in-memory eager task execution.")
    celery_app = Celery(
        "studyforge_tasks",
        broker="memory://",
        backend="cache+memory://",
        include=["app.tasks.document_tasks"]
    )

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

if not redis_available:
    # Execute celery tasks synchronously inline for easy local development
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True
    )
