import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.modules.users.models import User


async def purge_unverified_users(session: AsyncSession) -> int:
    """Delete users that never verified within the configured TTL.

    Kept as a plain async function so it is unit-testable without a broker.
    """
    cutoff = datetime.now(UTC) - timedelta(days=settings.unverified_user_ttl_days)
    result = await session.execute(
        delete(User).where(User.is_verified.is_(False), User.created_at < cutoff)
    )
    await session.commit()
    return result.rowcount


@celery_app.task(name="app.tasks.delete_expired_unverified_users")
def delete_expired_unverified_users() -> int:
    """Celery beat entrypoint (hourly). See purge_unverified_users for the logic.

    SIMPLIFICATION: asyncio.run per task invocation creates a fresh event loop
    and engine connections each run; fine at this scale. With more time, use a
    sync engine here or a shared loop per worker process.
    """

    async def _run() -> int:
        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            return await purge_unverified_users(session)

    return asyncio.run(_run())
