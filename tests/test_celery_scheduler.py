import json
import time
import os

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from celery_sqlalchemy_kit.db import crud


@pytest.fixture(scope="function")
def ac_session() -> Session:
    """An auto-committing session, this means all changes are directly committed to the DB.
    The changes are thus readable by other Connections."""
    engine = create_engine(
        os.getenv("SCHEDULER_DB_URI"),
        pool_size=2,
        max_overflow=10,
        pool_pre_ping=True,
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    connection = engine.connect()
    session = Session(bind=connection, expire_on_commit=False)

    try:
        yield session
    except Exception as e:
        raise e
    finally:
        session.close()
        connection.close()
        engine.dispose()


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
    # and only works when no other tests have been executed yet

    # check if routine that is in db but not in code was correctly deleted in db
    routine = crud.find_by_name(db=ac_session, name="test routine")
    assert not routine
    # check if routine that is in code and db but with different schedule keeps the schedule in db
    routine = crud.find_by_name(db=ac_session, name="celery test")
    assert routine.schedule == {"timedelta": 60}
    # check if routine that is in code and db but set inactive is not in schedule but still in db
    routine = crud.find_by_name(db=ac_session, name="celery test too")
    assert routine.active is False

    # activate both test tasks
    routine = crud.find_by_name(db=ac_session, name="celery test")
    obj_in = {"active": True}
    crud.update(db=ac_session, db_obj=routine, obj_in=obj_in)
    routine = crud.find_by_name(db=ac_session, name="celery test too")
    obj_in = {"active": True}
    crud.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # update schedule from task to every 5 seconds
    routine = crud.find_by_name(db=ac_session, name="celery test")
    obj_in = {"schedule": {"timedelta": 5}}
    crud.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # check if task is running
    with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        if "value" in test_file:
            value = test_file["value"]
    time.sleep(12)
    with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        value_new = test_file["value"]

    assert value_new > value

    # now set task inactive
    routine = crud.find_by_name(db=ac_session, name="celery test")
    obj_in = {"active": False}
    crud.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # check that task is not running
    with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        if "value" in test_file:
            value = test_file["value"]
    time.sleep(11)
    with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        value_new = test_file["value"]

    assert value_new == value

    # and now active again
    routine = crud.find_by_name(db=ac_session, name="celery test")
    obj_in = {"active": True}
    crud.update(db=ac_session, db_obj=routine, obj_in=obj_in)

    # check if task is running
    with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "r") as jsonFile:
        test_file = json.load(jsonFile)
        if "value" in test_file:
            value = test_file["value"]
    time.sleep(10)
    with open(os.getenv("CELERY_TEST_FILE", "celery_test.json"), "r") as jsonFile:
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
    routine = crud.find_by_name(db=ac_session, name="celery test")
    assert routine
    routine = crud.find_by_name(db=ac_session, name="celery test too")
    assert routine
