import logging

from celery import Celery

# examples for config
result_backend = "redis://redis:6379"
broker_url = "redis://redis:6379"
scheduler_db_uri = "psycopg2:///schedule.db"
worker_async_db_uri = "asyncpg:///schedule.db"
scheduler_max_interval = 3 * 60
scheduler_sync_every = 3 * 60
celery_max_retry = 3
celery_retry_delay = 300
logger = logging.getLogger("celery")


celery = Celery(
    "celery", include=["celery_sqlalchemy_kit.example.custom_tasks"], backend=result_backend, broker=broker_url
)

celery.conf.update(
    {
        "scheduler_db_uri": scheduler_db_uri,
        # "worker_async_db_uri": worker_async_db_uri,
        "scheduler_max_interval": scheduler_max_interval,
        "scheduler_sync_every": scheduler_sync_every,
        "celery_max_retry": celery_max_retry,
        "celery_retry_delay": celery_retry_delay,
        "create_table": True,
    },
)
