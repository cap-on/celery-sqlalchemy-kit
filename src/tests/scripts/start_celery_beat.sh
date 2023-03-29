#!/bin/sh -ex

celery -A tests.celery_test_instance beat --loglevel=DEBUG --scheduler=scheduler.RoutineScheduler &
tail -f /dev/null