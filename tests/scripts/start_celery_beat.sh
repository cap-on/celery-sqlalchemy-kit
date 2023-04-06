#!/bin/sh -ex
# wait for db
sleep 5
celery -A tests.celery_test_instance beat --loglevel=DEBUG --scheduler=celery_sqlalchemy_kit.RoutineScheduler &
tail -f /dev/null