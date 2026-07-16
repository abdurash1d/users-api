import asyncio
import uuid
from collections.abc import Sequence

from app.core import security
from app.core.exceptions import PermissionDeniedError, UserNotFoundError
from app.modules.users.models import Role, User
from app.modules.users.repository import UserRepository


async def list_users(repo: UserRepository, limit: int, offset: int) -> Sequence[User]:
    return await repo.list(limit=limit, offset=offset)


async def get_user(repo: UserRepository, user_id: uuid.UUID) -> User:
    user = await repo.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError
    return user


async def update_user(
    repo: UserRepository,
    actor: User,
    user_id: uuid.UUID,
    *,
    first_name: str | None,
    last_name: str | None,
    password: str | None,
    role: Role | None,
    is_verified: bool | None,
    fields_set: set[str],
) -> User:
    """Partial update. Users may edit their own profile; admins may edit anyone.

    `role` and `is_verified` may only be changed by admins.
    """
    is_admin = actor.role == Role.ADMIN
    if not is_admin and actor.id != user_id:
        raise PermissionDeniedError
    if not is_admin and not fields_set.isdisjoint({"role", "is_verified"}):
        raise PermissionDeniedError

    user = await get_user(repo, user_id)
    if "first_name" in fields_set:
        user.first_name = first_name
    if "last_name" in fields_set:
        user.last_name = last_name
    if password is not None:
        # argon2 is CPU-bound (~30ms); run in a thread so it never blocks the event loop.
        user.hashed_password = await asyncio.to_thread(security.hash_password, password)
    if role is not None:
        user.role = role
    if is_verified is not None:
        user.is_verified = is_verified
    await repo.commit()
    return user


async def delete_user(repo: UserRepository, user_id: uuid.UUID) -> None:
    user = await get_user(repo, user_id)
    await repo.delete(user)
    await repo.commit()
