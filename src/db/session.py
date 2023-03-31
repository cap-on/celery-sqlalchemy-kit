import os

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


class SessionWrapper:
    """
    Session Wrapper for the celery scheduler.
    Allows
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


# class TaskDBAsync:
#     """For async celery workers"""
#
#     session: AsyncSession
#     connection: AsyncConnection
#
#     def __init__(self, scheduler_db_uri: str):
#         self.engine = create_async_engine(
#             scheduler_db_uri,
#             pool_size=2,
#             max_overflow=10,
#             pool_pre_ping=True,
#         )
#
#     async def connect(self):
#         self.connection = await self.engine.connect()
#         await self.connection.begin()
#         self.session = AsyncSession(bind=self.connection, expire_on_commit=False)
#
#     async def close(self):
#         await self.session.commit()
#         await self.connection.commit()
#         await self.session.close()
#         await self.connection.close()
#
#     async def rollback(self):
#         await self.session.rollback()


metadata = MetaData()
