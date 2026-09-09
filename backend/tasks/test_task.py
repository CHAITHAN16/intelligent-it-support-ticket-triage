from celery_app import celery_app


@celery_app.task(name="it_support.test_task")
def test_task(value: str) -> str:
    """Return a value unchanged to verify the broker-worker-result path."""
    return value
