import logging
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

if DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def _migrate_add_column(conn, table: str, column: str, col_type: str) -> None:
    try:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        logger.info(f"Migration: added column {table}.{column}")
    except Exception:
        pass


async def init_db():
    async with engine.begin() as conn:
        from database.models import User, ActiveUpgrade
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_add_column(conn, "users", "buildings_snapshot", "TEXT")
        await _migrate_add_column(conn, "active_upgrades", "village", "VARCHAR(32) DEFAULT 'home'")
