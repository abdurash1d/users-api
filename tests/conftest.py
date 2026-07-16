import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_session
from app.core.email import get_email_sender
from app.main import app
from app.modules.users import models  # noqa: F401  (register tables on Base.metadata)

# Overridable so CI (standard port 5432) and local dev (5433, to avoid clashing
# with a local PostgreSQL — see docker-compose.yml) can use different databases.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/users_test"
)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class RecordingEmailSender:
    """Test double that captures verification codes instead of sending them."""

    def __init__(self) -> None:
        self.codes: dict[str, str] = {}

    def send_verification_code(self, email: str, code: str) -> None:
        self.codes[email] = code


@pytest.fixture
def email_sender() -> RecordingEmailSender:
    sender = RecordingEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    return sender
