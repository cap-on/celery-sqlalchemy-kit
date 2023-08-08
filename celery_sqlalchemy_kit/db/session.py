import time

from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from celery.utils.log import get_logger

logger = get_logger(__name__)


class SessionWrapper:
    """
    Session Wrapper for the celery scheduler.
    Allows operations in db on autocommit.
    """

    session: Session
    db_tries: int = 0

    def __init__(self, scheduler_db_uri: str):
        self.engine = create_engine(
            scheduler_db_uri,
            pool_size=2,
            max_overflow=10,
            pool_pre_ping=True,
            future=True,
            isolation_level="AUTOCOMMIT",
        )
        self.connection = self.engine.connect()
        self.session = Session(bind=self.connection, expire_on_commit=False)

    def renew(self):
        try:
            self.session.close()
            self.connection.close()
            self.connection = self.engine.connect()
            self.session = Session(bind=self.connection, expire_on_commit=False)
        except SQLAlchemyError as e:
            if self.db_tries > 2:
                logger.critical(e)
                time.sleep(5)
                raise e
            self.db_tries += 1
            self.renew()
        self.db_tries = 0

    def close(self):
        self.session.close()
        self.connection.close()


metadata = MetaData()
