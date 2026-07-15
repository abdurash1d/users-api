from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Role, User


async def test_create_user(db_session: AsyncSession) -> None:
    user = User(email="a@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    found = (
        await db_session.execute(select(User).where(User.email == "a@example.com"))
    ).scalar_one()
    assert found.role == Role.USER
    assert found.is_verified is False
    assert found.id is not None
    assert found.created_at is not None
