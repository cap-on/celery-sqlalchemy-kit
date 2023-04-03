#!/bin/sh -ex

celery -A tests.celery_test_instance worker --loglevel=DEBUG --pool=solo &
tail -f /dev/null