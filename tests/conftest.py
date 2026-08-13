import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.deps import get_session
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/anitrack_test"

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


async def _ensure_test_database():
    url = make_url(TEST_DATABASE_URL)
    admin = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database="postgres",
    )
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await admin.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    """A session whose writes are always rolled back, even after commit()."""
    async with engine.connect() as conn:
        await conn.begin()
        test_session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        yield test_session
        await test_session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    await client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "username": "tester",
            "email": "tester@example.com",
            "password": "hunter2hunter2",
        },
    )
    response = await client.post(
        "/auth/login",
        data={"username": "tester", "password": "hunter2hunter2"},
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
