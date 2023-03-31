import asyncio
import os

from celery import Task
from celery.utils.log import get_logger
from celery.schedules import crontab

# from db.session import TaskDBAsync

logger = get_logger(__name__)

# @AL Ich glaube, wir können das mit der Async Datenbankverbindung rauslassen.
# Ist ja nicht gesichert, dass sie async nur/ausschließlich mit async db connection wollen
# Kann man ja dann in die execute methode schreiben


class SyncTask(Task):
    """
    This celery Task class automatically saves scheduled tasks into your DB.
    If no schedule is set, the task is not being scheduled.
    Write your custom task by inheriting from this class and defining its 'run' method.

    All tasks can be executed on demand by using standard celery methods
    like 'async_apply()', 'delay()' or 'send_task()'.
    """

    name: str
    max_retries: int
    retry_delay: int
    schedule: int | dict | None = None
    options: dict = {}
    kwargs: dict = {}

    def __init__(self):
        if self.app.conf.get("celery_max_retry"):
            self.max_retries = int(self.app.conf.get("celery_max_retry"))
        else:
            self.max_retries = int(os.getenv("DEFAULT_CELERY_MAX_RETRY", 3))

        if self.app.conf.get("celery_retry_delay"):
            self.retry_delay = int(self.app.conf.get("celery_retry_delay"))
        else:
            self.retry_delay = int(os.getenv("DEFAULT_CELERY_RETRY_DELAY", 300))

        if self.schedule:
            self.schedule_task()

    def run(self, *args, **kwargs):
        """The body of the task executed by workers."""
        raise NotImplementedError("Synchronous Tasks must define the run method.")

    def schedule_task(self):
        self.app.add_periodic_task(
            self.set_schedule(self.schedule),
            self.s(**self.kwargs),
            name=self.name,
            **self.options
        )

    def set_schedule(self, schedule: int | dict):
        if isinstance(schedule, int):
            return schedule
        if isinstance(schedule, dict):
            return crontab(**schedule)
        logger.error("Bad schedule.")
        return None


class AsyncTask(SyncTask):
    """
    This Task class allows you to run async methods with celery.
    Write your custom task by inheriting from this class and defining its async 'execute' method.

    This celery Task automatically saves scheduled tasks into your DB.
    If no schedule is set, the task is not being scheduled.
    All tasks can be executed on demand by using standard celery methods
    like 'async_apply()', 'delay()' or 'send_task()'.
    """
    # _worker_async_db_uri: str = None

    # def __init__(self):
    #     super().__init__()
    #     self._worker_async_db_uri = (
    #         self.app.conf.get("worker_async_db_uri")
    #         or os.getenv("WORKER_ASYNC_DB_URI")
    #      )
    #     if not self._worker_async_db_uri:
    #         raise ValueError("Neither the celery config variable 'worker_async_db_uri' nor the ENV variable "
    #                      "'WORKER_ASYNC_DB_URI' is set.")

    def run(self, *args, **kwargs):
        try:
            asyncio.run(self.run_execute(*args, **kwargs))
        except Exception as e:
            raise self.retry(exc=e, max_retries=self.max_retries, retry_delay=self.retry_delay)

    async def run_execute(self, *args, **kwargs):
        # task_db = TaskDBAsync(scheduler_db_uri=self._worker_async_db_uri)
        # await task_db.connect()
        try:
            result = await self.execute(*args, **kwargs)
        except Exception as e:
            logger.error(e, exc_info=True)
            # await task_db.rollback()
            # await task_db.close()
            raise e
        else:
            # await task_db.close()
            if result:
                logger.info(result)

    async def execute(self, *args, **kwargs):
        """The body of the task executed by workers."""
        raise NotImplementedError("Asynchronous Tasks must define the execute method.")
