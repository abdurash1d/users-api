import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.database import get_session
from app.modules.users.models import Role, User
from app.modules.users.repository import UserRepository

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Resolve the Bearer access token to a User or raise 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = security.decode_token(credentials.credentials, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (security.TokenError, KeyError, ValueError):
        raise unauthorized from None
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_verified:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    """Allow only admins; raise 403 otherwise."""
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
