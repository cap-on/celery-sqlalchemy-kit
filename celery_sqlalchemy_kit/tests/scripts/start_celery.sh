#!/bin/sh -ex
# wait for db
sleep 5
celery -A tests.celery_test_instance worker --loglevel=DEBUG --pool=solo &
tail -f /dev/null