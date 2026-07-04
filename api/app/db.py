"""Async database access (SQLAlchemy 2.0 + asyncpg).

The schema itself is owned by the Supabase migration, not by SQLAlchemy — these
models mirror it for querying. The backend connects with the project's Postgres
credentials and always scopes queries by `user_id` derived from the JWT; RLS is
the second layer.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def _to_asyncpg_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


@lru_cache
def get_engine() -> AsyncEngine:
    """Create the async engine lazily (so imports don't require DATABASE_URL)."""
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return create_async_engine(
        _to_asyncpg_url(url),
        pool_pre_ping=True,
        # statement_cache_size=0 keeps us compatible with Supabase's connection
        # pooler; prefer the Session/direct connection string for a long-lived
        # service (see api/README.md).
        connect_args={"statement_cache_size": 0},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session."""
    async with get_sessionmaker()() as session:
        yield session
