import logging
import os

from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, Session
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init() -> None:
    engine = create_engine(
        os.getenv("SCHEDULER_DB_URI"),
        pool_size=2,
        max_overflow=10,
        pool_pre_ping=True,
    )
    sync_session = sessionmaker(engine, class_=Session, expire_on_commit=False)
    try:
        with sync_session() as session:
            session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(e)
        raise e


def main() -> None:
    print("Initializing service (waiting for DB)")
    init()


if __name__ == "__main__":
    main()
