from __future__ import annotations

import os

from celery import Celery


DEFAULT_REDIS_URL = "redis://localhost:6379/0"
REDIS_URL = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)


def create_celery_app(redis_url: str = REDIS_URL) -> Celery:
    app = Celery("it_support", broker=redis_url, backend=redis_url)
    app.conf.update(
        accept_content=["json"],
        enable_utc=True,
        result_serializer="json",
        task_serializer="json",
        timezone="UTC",
        imports=("tasks.test_task", "tasks.ticket_tasks"),
    )
    return app


celery_app = create_celery_app()
