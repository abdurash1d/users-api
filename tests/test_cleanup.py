import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import settings
from app.modules.users.models import User
from app.tasks import delete_expired_unverified_users, purge_unverified_users
from tests.conftest import TEST_DATABASE_URL


async def test_purge_deletes_only_expired_unverified(db_session: AsyncSession) -> None:
    old_unverified = User(email="old@example.com", hashed_password="x", is_verified=False)
    fresh_unverified = User(email="fresh@example.com", hashed_password="x", is_verified=False)
    old_verified = User(email="ok@example.com", hashed_password="x", is_verified=True)
    db_session.add_all([old_unverified, fresh_unverified, old_verified])
    await db_session.commit()

    three_days_ago = datetime.now(UTC) - timedelta(days=3)
    await db_session.execute(
        update(User)
        .where(User.email.in_(["old@example.com", "ok@example.com"]))
        .values(created_at=three_days_ago)
    )
    await db_session.commit()

    deleted = await purge_unverified_users(db_session)
    assert deleted == 1

    remaining = (await db_session.execute(select(User.email))).scalars().all()
    assert sorted(remaining) == ["fresh@example.com", "ok@example.com"]


async def test_celery_entrypoint_survives_repeat_invocations(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: run 2 must not reuse pooled connections from run 1's event loop."""
    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    first = await asyncio.to_thread(delete_expired_unverified_users)
    second = await asyncio.to_thread(delete_expired_unverified_users)
    assert first == 0
    assert second == 0
