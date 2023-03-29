import os

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


@pytest.fixture(scope="function")
def ac_session() -> Session:
    """An auto-committing session, this means all changes are directly committed to the DB.
    The changes are thus readable by other Connections."""
    engine = create_engine(
        os.getenv("SQLALCHEMY_DATABASE_SYNC_URI"),
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
