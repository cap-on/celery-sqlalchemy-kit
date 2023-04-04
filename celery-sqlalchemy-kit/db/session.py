from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import Session


class SessionWrapper:
    """
    Session Wrapper for the celery scheduler.
    Allows operations in db on autocommit.
    """

    session: Session

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
        self.session.close()
        self.connection.close()
        self.connection = self.engine.connect()
        self.session = Session(bind=self.connection, expire_on_commit=False)

    def close(self):
        self.session.close()
        self.connection.close()


metadata = MetaData()
