import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.db.base import create_all, make_engine, make_session_factory


@pytest_asyncio.fixture
async def session(tmp_path) -> AsyncSession:
    # A real temp file (rather than sqlite ":memory:") avoids per-connection
    # database isolation surprises from aiosqlite's connection pooling.
    db_path = tmp_path / "test.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    await create_all(engine)
    session_factory = make_session_factory(engine)
    async with session_factory() as s:
        yield s
    await engine.dispose()
