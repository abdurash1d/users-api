import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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

    A fresh engine is created and disposed per invocation: asyncio.run() creates
    a new event loop each time, and pooled asyncpg connections must never be
    reused across loops (doing so crashes on the second run in a worker).
    SIMPLIFICATION: with more time, set up one persistent event loop and engine
    per worker process via the worker_process_init signal instead of paying
    engine setup/teardown on every run.
    """

    async def _run() -> int:
        engine = create_async_engine(settings.database_url)
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                return await purge_unverified_users(session)
        finally:
            await engine.dispose()

    return asyncio.run(_run())
