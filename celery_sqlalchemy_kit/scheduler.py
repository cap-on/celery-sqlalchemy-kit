import os
from typing import List

from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_logger
from celery.beat import Scheduler

from sqlalchemy.exc import SQLAlchemyError

from db.model import Routine, Base
from sqlalchemy.orm import Session

from db.crud import crud
from db.session import SessionWrapper

DEFAULT_SCHEDULER_SYNC_DB_URI = "postgresql+psycopg2:///schedule.db"

logger = get_logger(__name__)


class RoutineScheduler(Scheduler):
    """Scheduler backed by Postgres or MySQL database."""

    #: Maximum time to sleep between re-checking the schedule. (5 minutes by default)
    max_interval: int
    #: How often to sync the schedule (3 minutes by default)
    sync_every: int
    #: How many tasks can be called before a sync is forced.
    sync_every_tasks = None
    _session: Session
    _db_routines: List[Routine] | None = None
    _db_routines_dict: dict | None = None

    def __init__(self, *args, **kwargs):

        self.app: Celery = kwargs["app"]
        db_uri = (
            self.app.conf.get("scheduler_db_uri")
            or os.getenv("SCHEDULER_DB_URI")
            or DEFAULT_SCHEDULER_SYNC_DB_URI
        )

        self.max_interval = int(self.app.conf.get("scheduler_max_interval") or os.getenv("SCHEDULER_MAX_INTERVAL", 10))

        self.sync_every = int(self.app.conf.get("scheduler_sync_every") or os.getenv("SCHEDULER_SYNC_EVERY", 3 * 60))

        self._task_db = SessionWrapper(scheduler_db_uri=db_uri)
        self._session = self._task_db.session

        if not self.app.conf.get("create_table", True):
            try:
                Base.metadata.create_all(bind=self._task_db.engine, checkfirst=True)
                # checkfirst = True: will not attempt to recreate tables already present in the target database.
            except Exception as e:
                logger.error(e, exc_info=True)

        self._to_be_updated = set()
        self._schedule = {}
        self.db_tries = 0
        super().__init__(*args, **kwargs)

    # Merge changes
    def merge_inplace(self, celery_task_schedules: dict):
        """
        This method merges routines in DB and routines defined in code of celery beat.
        It is being executed when starting celery.
        It follows the rules:
        - if a new schedule is defined in celery beat, it gets inserted into the DB
        - if a schedule is not defined in celery beat anymore, it gets deleted from DB
        - if tasks are in DB as well as celery beat, the entries in DB are the single source of truth

                        **Parameters**
        * `celery_task_schedules`: The schedules defined by celery beat on startup.
        """
        # schedule = self.schedule
        # get all routines from db, active and inactive
        db_routines = crud.get_multiple(db=self._session)
        schedule = self.db_routines_to_schedule_entries(db_routines=db_routines)

        # compare which routines are
        # new in celery routines -> write to db
        write_to_db = {}
        for key in celery_task_schedules:
            if key not in schedule:
                write_to_db[key] = celery_task_schedules[key]

        # deleted in celery -> delete in db
        delete_from_db = {}
        for key in schedule:
            if key not in celery_task_schedules:
                delete_from_db[key] = schedule[key]

        # Update db
        logger.debug("Setup: Update db.")
        self.update_db(write_to_db=write_to_db, delete_from_db=delete_from_db)

    def update_db(self, write_to_db: dict = None, delete_from_db: dict = None):
        """
        Updates the DB by inserting new schedules and deleting deprecated schedules.
        """
        if write_to_db:
            write_to_db = self.schedule_dict_to_db_routines(write_to_db)
            logger.debug("Setup: Add celery routines to db.")
            try:
                crud.create_multiple(db=self._session, routines_in=write_to_db)
            except Exception as e:
                logger.error(e, exc_info=True)
        if delete_from_db:
            routine_names = [key for key in delete_from_db]
            logger.debug("Setup: Delete celery routines from db.")
            try:
                crud.remove_by_name(db=self._session, names=routine_names)
            except Exception as e:
                logger.error(e, exc_info=True)

    def setup_schedule(self):
        self.merge_inplace(self.app.conf.beat_schedule)
        self.install_default_entries(self.schedule)

    def db_routines_to_schedule_entries(self, db_routines):
        schedule_entries = {}
        for routine in db_routines:
            routine_dict = routine.to_dict()
            del routine_dict["id"]
            del routine_dict["active"]
            # timedelta or crontab
            routine_dict["schedule"] = routine.schedule_object
            entry = self.Entry(**dict(routine_dict, name=routine.name, app=self.app))
            schedule_entries[routine.name] = entry
        return schedule_entries

    @staticmethod
    def schedule_dict_to_db_routines(schedule_dict):
        db_routines = []
        for key, value in schedule_dict.items():
            if isinstance(value["schedule"], int):
                schedule = {"timedelta": value["schedule"]}
            elif isinstance(value["schedule"], crontab):
                schedule = {
                    "minute": value["schedule"]._orig_minute,
                    "hour": value["schedule"]._orig_hour,
                    "day_of_week": value["schedule"]._orig_day_of_week,
                    "day_of_month": value["schedule"]._orig_day_of_month,
                    "month_of_year": value["schedule"]._orig_month_of_year,
                }
            else:
                raise ValueError(f"Schedule of task {key} is neither crontab nor an int")
            db_routines.append(
                Routine(
                    name=key,
                    task=value["task"],
                    schedule=schedule,
                    kwargs=value["kwargs"],
                    options=value["options"],
                )
            )
        return db_routines

    def get_schedule(self) -> dict:
        """
        Retrieve schedules from DB and return them as a db of schedule entries with schedule names as keys
        and entries as values.
        """
        logger.debug("get schedule")
        schedule_entries = {}
        try:
            self._db_routines = crud.get_multiple(db=self._session, active=True)
            schedule_entries = self.db_routines_to_schedule_entries(db_routines=self._db_routines)
        except SQLAlchemyError as e:
            if self.db_tries > 0:
                raise e
            self._task_db.renew()
            self._session = self._task_db.session
            self.db_tries = 1
            return self.get_schedule()
        except Exception as e:
            logger.error(e, exc_info=True)
        logger.debug("Current schedule:\n" + "\n".join(repr(entry) for entry in schedule_entries.values()))
        self.db_tries = 0
        return schedule_entries

    def set_schedule(self, new_schedule):
        logger.debug("set schedule")
        self._schedule = new_schedule

    schedule = property(get_schedule, set_schedule)

    def sync(self):
        """
        Updates the two columns 'last_run_at' and 'total_run_count' in DB for executed tasks.
        Runs frequently depending on 'sync_every' and 'sync_every_tasks'.
        """
        logger.debug("Update routines in DB.")
        _tried = set()
        _failed = set()
        if self._schedule:
            try:
                while self._to_be_updated:
                    name = self._to_be_updated.pop()
                    try:
                        # get db entry by name and update total_run_count and last_run_time
                        db_routine = [routine for routine in self._db_routines if routine.name == name]
                        if not db_routine:
                            logger.error(f"Could not find routine with name {name} in db.")
                        db_routine = db_routine[0]
                        # update last_run_at and total_run_count
                        obj_in = {
                            "last_run_at": self._schedule[name].last_run_at,
                            "total_run_count": self._schedule[name].total_run_count,
                        }
                        crud.update(db=self._session, db_obj=db_routine, obj_in=obj_in)
                        _tried.add(name)
                    except SQLAlchemyError as e:
                        if self.db_tries > 0:
                            raise e
                        self._task_db.renew()
                        self._session = self._task_db.session
                        self._db_routines = crud.get_multiple(db=self._session, active=True)
                        self.db_tries = 1
                        self._to_be_updated.add(name)
                        return self.sync()
                    except Exception as e:
                        _failed.add(name)
                        logger.error(e, exc_info=True)
                        logger.debug("Database error while sync: %r", e)
                    else:
                        self.db_tries = 0
            finally:
                # retry later, only for the failed ones
                self._to_be_updated |= _failed

    def reserve(self, entry):
        """
        Is being executed every tick (iteration) of the scheduler.
        Updates the next entry in heap and calls next() to update 'last_run_at' and 'total_run_count'.
        """
        new_entry = next(entry)
        self._schedule[entry.name] = new_entry
        # Need to store entry by name, because the entry may change in the meantime.
        self._to_be_updated.add(new_entry.name)
        return new_entry

    def close(self):
        self.sync()
        self._task_db.close()
