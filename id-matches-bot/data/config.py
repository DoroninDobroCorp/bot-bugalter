from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, MetaData
from pathlib import Path


# Resolve path to main.db at the repository root
DB_PATH = (Path(__file__).resolve().parents[2] / "main.db").as_posix()
async_engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")

async_session = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
