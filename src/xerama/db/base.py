"""Async SQLAlchemy engine/session setup.

Domain and pipeline code must never import this module directly - go through
`xerama.repositories`. That boundary is what lets PostgreSQL replace SQLite
later without touching story/production logic (ADR-021).
"""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_last_utcnow: datetime | None = None


def utcnow() -> datetime:
    """Real UTC wall-clock time, but strictly increasing within this
    process - some platforms' clock resolution (observed on Windows) is
    coarse enough that two `created_at` defaults evaluated microseconds
    apart (e.g. two rows inserted in the same request) can come back
    identical, which silently breaks any code that orders by `created_at`
    to recover insertion order (e.g. `JobRepository.claim`'s FIFO
    tie-break, `MediaQCRepository.get_latest`). Nudging by a microsecond
    when the clock hasn't visibly advanced keeps every timestamp real and
    monotonic without a schema change; true cross-process ordering still
    needs a DB-side sequence, which is out of scope for a single-process
    Trial 01 deployment."""
    global _last_utcnow
    now = datetime.now(timezone.utc)
    if _last_utcnow is not None and now <= _last_utcnow:
        now = _last_utcnow + timedelta(microseconds=1)
    _last_utcnow = now
    return now


def make_engine(database_url: str):
    connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}
    # MODULE-070 - `pool_pre_ping` issues a lightweight liveness check
    # before handing out a pooled connection, so a connection gone stale
    # (DB restart, network blip, a hosted DB's idle-connection timeout)
    # is transparently replaced instead of failing the next real query
    # with a cryptic "server closed the connection" error. A no-op cost
    # for SQLite's single local connection; the hardening this exists
    # for is a hosted PostgreSQL deployment (section 7,
    # docs/DEPLOYMENT.md).
    return create_async_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


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
