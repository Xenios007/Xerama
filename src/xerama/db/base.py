"""Async SQLAlchemy engine/session setup.

Domain and pipeline code must never import this module directly - go through
`xerama.repositories`. That boundary is what lets PostgreSQL replace SQLite
later without touching story/production logic (ADR-021).
"""

from collections.abc import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_engine(database_url: str):
    connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}
    return create_async_engine(database_url, connect_args=connect_args)


def make_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_all(engine) -> None:
    """Create tables from metadata. Trial 01 convenience - real deployments
    should use the Alembic migrations in alembic/versions/."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SessionScope:
    """Small async-context-manager wrapper so callers don't import SQLAlchemy directly."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session
