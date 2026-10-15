"""SQLAlchemy async engine and session factory.

Supports both SQLite (aiosqlite) for development and
PostgreSQL (asyncpg) for production, selected via DATABASE_URL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # SQLite does not support pool_pre_ping; PostgreSQL does
    **({"pool_pre_ping": True} if not _is_sqlite else {"connect_args": {"check_same_thread": False}}),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
