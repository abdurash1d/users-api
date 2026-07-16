import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.modules.auth.dependencies import AdminUser, CurrentUser
from app.modules.users import service
from app.modules.users.dependencies import RepoDep
from app.modules.users.schemas import UserRead, UserUpdate

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user",
    description="Returns the profile of the authenticated user.",
)
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="List users (admin)",
    description="Returns a paginated list of users. Admin only.",
)
async def list_users(
    _: AdminUser,
    repo: RepoDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserRead]:
    users = await service.list_users(repo, limit=limit, offset=offset)
    return [UserRead.model_validate(u) for u in users]


@router.get(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Get user by ID (admin)",
    description="Returns a single user by ID. Admin only.",
)
async def read_user(user_id: uuid.UUID, _: AdminUser, repo: RepoDep) -> UserRead:
    return UserRead.model_validate(await service.get_user(repo, user_id))


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Update user",
    description="Partially updates a user. Users may edit their own profile "
    "(name, password); admins may edit anyone, including role and verified status.",
)
async def update_user(
    user_id: uuid.UUID, data: UserUpdate, current_user: CurrentUser, repo: RepoDep
) -> UserRead:
    user = await service.update_user(
        repo,
        current_user,
        user_id,
        first_name=data.first_name,
        last_name=data.last_name,
        password=data.password,
        role=data.role,
        is_verified=data.is_verified,
        fields_set=data.model_fields_set,
    )
    return UserRead.model_validate(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user (admin)",
    description="Deletes a user by ID. Admin only.",
)
async def delete_user(user_id: uuid.UUID, _: AdminUser, repo: RepoDep) -> None:
    await service.delete_user(repo, user_id)
