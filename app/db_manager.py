import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from sqlalchemy.pool import NullPool
from app.config import settings

Base = declarative_base()


class DBManager:

    def __init__(self):
        self.config = settings
        self.engine = None
        self.session_factory = None
        self.Base = declarative_base()
        self.logger_handler_instance = None

    def initialize(self, logger_handler_instance):
        self.logger_handler_instance = logger_handler_instance
        # https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
        self.engine = create_async_engine(self.config.database_url, pool_pre_ping=True, echo_pool=True, echo=False,
                                          pool_recycle=3600, poolclass=NullPool)
        DBManager.Base = declarative_base()
        self.session_factory = scoped_session(
            sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        )

    async def get_db_session(self):
        session = self.session_factory()

        try:
            return session
        except Exception as e:
            self.logger_handler_instance.log(__name__, logging.FATAL,
                                             "Session rollback because of exception")
            self.logger_handler_instance.log(__name__, logging.FATAL, e)
            await session.rollback()
            raise
        finally:
            await session.close()

    async def init_models(self):
        async with self.engine.begin() as conn:
            # Create tables if they don't already exist
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
