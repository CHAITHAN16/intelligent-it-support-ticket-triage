import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from celery import Celery

from celery_app import DEFAULT_REDIS_URL, REDIS_URL, celery_app, create_celery_app
from tasks.test_task import test_task


def test_celery_uses_configured_redis_url():
    assert REDIS_URL == os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
    assert celery_app.conf.broker_url == REDIS_URL
    assert celery_app.conf.result_backend == REDIS_URL


def test_celery_factory_accepts_an_override():
    configured_app = create_celery_app("redis://example.test:6380/4")

    assert isinstance(configured_app, Celery)
    assert configured_app.conf.broker_url == "redis://example.test:6380/4"
    assert configured_app.conf.result_backend == "redis://example.test:6380/4"


def test_test_task_is_registered_without_a_live_broker():
    assert "it_support.test_task" in celery_app.tasks
    assert test_task.run("hello") == "hello"
