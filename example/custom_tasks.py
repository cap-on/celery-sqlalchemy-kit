import json
import os

from example.celery_app import celery
from celery_sqlalchemy_kit.base_task import AsyncTask, SyncTask

CELERY_TEST_FILE: str = os.getenv("CELERY_TEST_FILE")


class CeleryTestTask(SyncTask):

    name = "celery test"
    schedule = 15

    def run(self, *args, **kwargs):
        with open(CELERY_TEST_FILE, "r") as jsonFile:
            test_file = json.load(jsonFile)
            value = test_file["value"]
            value2 = test_file["value2"]

        with open(CELERY_TEST_FILE, "w") as jsonFile:
            json.dump({"value": value + 1, "value2": value2}, jsonFile)


class CeleryTestTaskToo(AsyncTask):

    name = "celery test too"
    schedule = 15

    async def execute(self, *args, **kwargs):
        with open(CELERY_TEST_FILE, "r") as jsonFile:
            test_file = json.load(jsonFile)
            value = test_file["value"]
            value2 = test_file["value2"]

        with open(CELERY_TEST_FILE, "w") as jsonFile:
            json.dump({"value": value, "value2": value2 + 1}, jsonFile)


CeleryTestTask = celery.register_task(CeleryTestTask())
CeleryTestTaskToo = celery.register_task(CeleryTestTaskToo())
