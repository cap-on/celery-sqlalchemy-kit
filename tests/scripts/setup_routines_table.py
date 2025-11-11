import logging
import os
import string
from random import choices

from celery_sqlalchemy_kit.db import crud
from celery_sqlalchemy_kit.db import Base, Routine
from celery_sqlalchemy_kit.db import SessionWrapper


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def setup_db_for_celery_test() -> None:
    task_db = SessionWrapper(scheduler_db_uri=os.getenv("SCHEDULER_DB_URI"))
    try:
        logger.debug("create 'routines' table")
        # create routines table
        Base.metadata.create_all(bind=task_db.engine, checkfirst=True)

        # prepare db
        # delete all entries in 'routines' table
        crud.remove_all(db=task_db.session)
        # create routine in db that is not defined in code
        routine = get_random_routine(name="test routine")
        crud.create(db=task_db.session, routine_in=Routine(**routine))
        # create routine, that is defined in code but with different schedule
        routine = get_random_routine(name="celery test", task="celery test", schedule={"timedelta": 60})
        crud.create(db=task_db.session, routine_in=Routine(**routine))
        # create routine that is defined in code but set inactive in db
        routine = get_random_routine(name="celery test too", task="celery test too", active=False)
        crud.create(db=task_db.session, routine_in=Routine(**routine))
        task_db.session.commit()
    except Exception as e:
        logger.error(e)
    finally:
        task_db.close()


def get_random_routine(name: str = None, task: str = None, schedule: dict = None, active: bool = True) -> dict:
    schedule = {"timedelta": 20} if schedule is None else schedule
    name = random_lower_string() if name is None else name
    task = random_lower_string() if task is None else task
    return {"name": name, "task": task, "schedule": schedule, "active": active}


def random_lower_string(k=10) -> str:
    return "".join(choices(string.ascii_lowercase, k=k))


if __name__ == "__main__":
    setup_db_for_celery_test()
    logger.debug("db is ready for celery tests")
