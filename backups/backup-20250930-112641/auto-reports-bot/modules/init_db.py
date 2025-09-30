from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pathlib import Path


DB_PATH = (Path(__file__).resolve().parents[2] / "main.db").as_posix()
async_engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")

async_session = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
