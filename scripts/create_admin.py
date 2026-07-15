"""Bootstrap an admin user: uv run python -m scripts.create_admin <email> <password>.

Creates a verified admin, or promotes an existing user to admin and resets their
password.
"""

import asyncio
import sys

from sqlalchemy.exc import IntegrityError

from app.core import security
from app.core.database import async_session_factory
from app.modules.users.models import Role, User
from app.modules.users.repository import UserRepository


async def create_admin(email: str, password: str) -> None:
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email(email.lower())
        if user is None:
            user = User(
                email=email.lower(),
                hashed_password=security.hash_password(password),
                role=Role.ADMIN,
                is_verified=True,
            )
            repo.add(user)
        else:
            user.role = Role.ADMIN
            user.is_verified = True
            user.hashed_password = security.hash_password(password)
        await repo.commit()
        print(f"Admin ready: {user.email}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python -m scripts.create_admin <email> <password>")
    try:
        asyncio.run(create_admin(sys.argv[1], sys.argv[2]))
    except OSError as exc:
        sys.exit(
            f"Could not reach the database ({exc}). "
            "Is the db service running (docker compose up -d db)?"
        )
    except IntegrityError:
        sys.exit("A concurrent invocation already created this user - re-run to promote it.")
