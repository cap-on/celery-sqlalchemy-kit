#!/bin/sh -ex
python scripts/prestart.py
# wait for db
sleep 3
python tests/setup_routines_table.py
# wait for celery worker and beat to setup
sleep 10
pytest tests