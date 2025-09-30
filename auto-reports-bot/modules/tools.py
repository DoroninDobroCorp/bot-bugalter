import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from modules.init_db import async_session, async_engine

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def session_scope() -> AsyncSession:
	session = async_session()
	try:
		yield session
		await session.commit()
	except Exception as e:
		_logger.error("session scope error: {}".format(e))
		await session.rollback()
		raise
	finally:
		await session.close()


async def init_models(model: DeclarativeBase):
	async with async_engine.begin() as conn:
		# await conn.run_sync(model.metadata.drop_all)
		await conn.run_sync(model.metadata.create_all)

