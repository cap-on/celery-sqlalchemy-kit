import time

from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DBAPIError, InterfaceError
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
            pool_recycle=1800,
            future=True,
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 5},
        )
        self._establish_session_with_retry()

    def _establish_session_with_retry(self):
        """Create a fresh connection and session, retrying until the DB becomes available."""
        delay = 1
        while True:
            try:
                self.connection = self.engine.connect()
                self.session = Session(bind=self.connection, expire_on_commit=False)
                self.db_tries = 0
                return
            except (OperationalError, DBAPIError, InterfaceError, SQLAlchemyError):
                self.db_tries += 1
                logger.warning(
                    "DB connect failed (try %s); retrying in %ss",
                    self.db_tries, delay, exc_info=True
                )
                time.sleep(delay)
                delay = min(delay * 2, 30)

    def renew(self):
        """Dispose broken connections and recreate session with exponential backoff."""
        # Best-effort cleanup of current handles
        try:
            try:
                self.session.close()
            except Exception:
                pass
            try:
                self.connection.close()
            except Exception:
                pass
            # Force pool to drop any stale/broken sockets
            self.engine.dispose()
        except Exception:
            pass
        # Reconnect until DB is back
        self._establish_session_with_retry()

    def close(self):
        try:
            self.session.close()
        finally:
            try:
                self.connection.close()
            finally:
                try:
                    self.engine.dispose()
                except Exception:
                    pass


metadata = MetaData()
