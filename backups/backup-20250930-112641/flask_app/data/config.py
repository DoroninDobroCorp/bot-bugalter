from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, MetaData


async_engine = create_async_engine("sqlite+aiosqlite:///../main.db")

async_session = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
