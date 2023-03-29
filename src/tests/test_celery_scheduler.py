import json
import os
import time

import pytest
from sqlalchemy.orm import Session
from crud_routines import crud_routine


# @pytest.mark.skip
def test_celery_scheduler(ac_session: Session) -> None:
    """
    This tests our RoutineScheduler by using the celery_test_instance in celery_test_instance.py.
    In the first part it is being tested, if the scheduler sets up the routines in the DB correctly. Since this only
    happens on startup, this part of the test only works correctly the first time after starting the scheduler.
    Also, the files 'scripts/prestart.py' and 'tests/setup_routines_table.py' must be executed in advance.
    Before the test is being run again, the scheduler needs to be restarted.
    """
    time.sleep(7)

    # this part checks if the schedule is set up correctly (merge db entries and celery routines correctly)
    # and only works when docker when no other tests have been executed yet

    # check if routine that is in db but not in code was correctly deleted in db
    routine = crud_routine.find_by_name(db=ac_session, name="test routine")
    assert not routine
    # check if routine that is in code and db but with different schedule keeps the schedule in db
    routine = crud_routine.find_by_name(db=ac_session, name="celery test")
    assert routine.schedule == {"timedelta": 60}
    # check if routine that is in code and db but set inactive is not in schedule but still in db
    routine = crud_routine.find_by_name(db=ac_session, name="celery test too")
    assert routine.active is False

    # activate both test tasks
    routine = crud_routine.find_by_name(db=ac_session, name="celery test")
    obj_in = {"active": True}
    crud_routine.update(db=ac_session, db_obj=routine, obj_in=obj_in)
    routine = crud_routine.find_by_name(db=ac_session, name="celery test too")
    obj_in = {"active": True}
    crud_routine.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # update schedule from task to every 5 seconds
    routine = crud_routine.find_by_name(db=ac_session, name="celery test")
    obj_in = {"schedule": {"timedelta": 5}}
    crud_routine.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # check if task is running
    with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        if "value" in test_file:
            value = test_file["value"]
    time.sleep(10)
    with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        value_new = test_file["value"]

    assert value_new > value

    # now set task inactive
    routine = crud_routine.find_by_name(db=ac_session, name="celery test")
    obj_in = {"active": False}
    crud_routine.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # check that task is not running
    with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        if "value" in test_file:
            value = test_file["value"]
    time.sleep(11)
    with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        value_new = test_file["value"]

    assert value_new == value

    # and now active again
    routine = crud_routine.find_by_name(db=ac_session, name="celery test")
    obj_in = {"active": True}
    crud_routine.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # check if task is running
    with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        if "value" in test_file:
            value = test_file["value"]
    time.sleep(10)
    with open(os.getenv("CELERY_TEST_FILE"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        value_new = test_file["value"]

    assert value_new > value


@pytest.mark.skip
def test_create_table_by_scheduler(ac_session: Session) -> None:
    """
    This tests if the scheduler creates table 'routines' on startup if 'use_alembic=False' is set in celery config.
    Don't use 'tests/setup_routines_table.py' for this test.
    """
    # check if table 'routines' is set up by scheduler and routine entries are available
    routine = crud_routine.find_by_name(db=ac_session, name="celery test")
    assert routine
    routine = crud_routine.find_by_name(db=ac_session, name="celery test too")
    assert routine
