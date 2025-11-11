#!/bin/sh -ex
python tests/scripts/prestart.py
# wait for db
sleep 3
python tests/scripts/setup_routines_table.py
# wait for celery worker and beat to setup
#sleep 10
#pytest tests
tail -f /dev/null