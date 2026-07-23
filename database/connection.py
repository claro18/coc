import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

if DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for thread-based web server
_sync_db_url = os.getenv("DATABASE_URL", "sqlite:///./bot.db")
if _sync_db_url.startswith("postgresql+asyncpg://"):
    _sync_db_url = _sync_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
elif _sync_db_url.startswith("sqlite+aiosqlite://"):
    _sync_db_url = _sync_db_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
sync_engine = create_engine(_sync_db_url, echo=False, pool_pre_ping=True)
sync_session = sessionmaker(bind=sync_engine, class_=Session)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def _column_exists(conn, table: str, column: str) -> bool:
    try:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :col"
            ),
            {"table": table, "col": column},
        )
        return result.scalar() is not None
    except Exception:
        return False


async def _migrate_add_column(conn, table: str, column: str, col_type: str) -> None:
    if await _column_exists(conn, table, column):
        logger.info(f"Migration: column {table}.{column} already exists, skipping")
        return
    try:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        logger.info(f"Migration: added column {table}.{column}")
    except Exception as e:
        logger.warning(f"Migration: failed to add {table}.{column}: {e}")


async def init_db():
    async with engine.begin() as conn:
        from database.models import User, ActiveUpgrade
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_add_column(conn, "users", "buildings_snapshot", "TEXT")
        await _migrate_add_column(conn, "active_upgrades", "village", "TEXT DEFAULT 'home'")
