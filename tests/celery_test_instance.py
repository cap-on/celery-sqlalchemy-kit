import json
import os

from celery import Celery
from celery_sqlalchemy_kit.base_task import AsyncTask

celeryTest = Celery(
    "celeryTest",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend=os.getenv("CELERY_RESULT_BACKEND"),
)

celeryTest.conf.update(
    {
        "scheduler_db_uri": os.getenv("SCHEDULER_DB_URI"),
        "scheduler_max_interval": os.getenv("SCHEDULER_MAX_INTERVAL"),
        "scheduler_sync_every": os.getenv("SCHEDULER_SYNC_EVERY"),
        "create_table": True,
    }
)

with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "w") as jsonFile:
    json.dump({"value": 0, "value2": 0}, jsonFile)


class CeleryTestTask(AsyncTask):

    name = "celery test"
    schedule = 15

    def __init__(self):
        super().__init__()

    async def execute(self, *args, **kwargs):
        with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
            test_file = json.load(jsonFile)
            value = test_file["value"]
            value2 = test_file["value2"]

        with open(os.getenv("CELERY_TEST_FILE"), "w") as jsonFile:
            json.dump({"value": value + 1, "value2": value2}, jsonFile)


class CeleryTestTaskToo(AsyncTask):

    name = "celery test too"
    schedule = 15

    def __init__(self):
        super().__init__()

    async def execute(self, *args, **kwargs):
        with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
            test_file = json.load(jsonFile)
            value = test_file["value"]
            value2 = test_file["value2"]

        with open(os.getenv("CELERY_TEST_FILE"), "w") as jsonFile:
            json.dump({"value": value, "value2": value2 + 1}, jsonFile)


CeleryTestTask = celeryTest.register_task(CeleryTestTask())
CeleryTestTaskToo = celeryTest.register_task(CeleryTestTaskToo())
