from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base
from app.storage.object_store import InMemoryObjectStore, get_object_store


@pytest_asyncio.fixture
async def engine():
    """A fresh in-memory SQLite database per test (StaticPool keeps the single
    in-memory connection alive across sessions)."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def client(engine):
    """HTTP client wired to the test DB and an in-memory object store."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db():
        async with session_factory() as session:
            yield session

    store = InMemoryObjectStore()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_object_store] = lambda: store

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()
