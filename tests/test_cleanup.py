from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.tasks import purge_unverified_users


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
