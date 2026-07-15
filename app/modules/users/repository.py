import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    """Thin data-access layer over the users table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        # Emails are stored lowercased; normalize lookups so no caller can miss it.
        email = email.lower()
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> Sequence[User]:
        result = await self._session.execute(
            select(User).order_by(User.created_at, User.id).limit(limit).offset(offset)
        )
        return result.scalars().all()

    def add(self, user: User) -> None:
        self._session.add(user)

    async def delete(self, user: User) -> None:
        await self._session.delete(user)

    async def commit(self) -> None:
        await self._session.commit()
