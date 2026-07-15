import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.modules.users.models import Role, User


async def make_user(
    db_session: AsyncSession, email: str, role: Role = Role.USER, verified: bool = True
) -> User:
    user = User(
        email=email,
        hashed_password=security.hash_password("password123"),
        role=role,
        is_verified=verified,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.create_access_token(user.id, user.role)}"}


async def test_me_returns_current_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    resp = await client.get("/me", headers=auth_header(user))
    assert resp.status_code == 200
    assert resp.json()["email"] == "u@example.com"


async def test_me_without_token_unauthorized(client: AsyncClient) -> None:
    resp = await client.get("/me")
    assert resp.status_code == 401


async def test_list_users_admin_only(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    admin = await make_user(db_session, "a@example.com", role=Role.ADMIN)

    assert (await client.get("/users", headers=auth_header(user))).status_code == 403
    resp = await client.get("/users", headers=auth_header(admin))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_user_by_id_admin_only(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    admin = await make_user(db_session, "a@example.com", role=Role.ADMIN)

    assert (await client.get(f"/users/{user.id}", headers=auth_header(user))).status_code == 403
    resp = await client.get(f"/users/{user.id}", headers=auth_header(admin))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(user.id)


async def test_get_missing_user_404(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await make_user(db_session, "a@example.com", role=Role.ADMIN)
    resp = await client.get(f"/users/{uuid.uuid4()}", headers=auth_header(admin))
    assert resp.status_code == 404


async def test_patch_self_allowed(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    resp = await client.patch(
        f"/users/{user.id}", headers=auth_header(user), json={"first_name": "New"}
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "New"


async def test_patch_other_user_forbidden(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    other = await make_user(db_session, "o@example.com")
    resp = await client.patch(
        f"/users/{other.id}", headers=auth_header(user), json={"first_name": "Hack"}
    )
    assert resp.status_code == 403


async def test_patch_role_requires_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    resp = await client.patch(
        f"/users/{user.id}", headers=auth_header(user), json={"role": "admin"}
    )
    assert resp.status_code == 403

    admin = await make_user(db_session, "a@example.com", role=Role.ADMIN)
    resp = await client.patch(
        f"/users/{user.id}", headers=auth_header(admin), json={"role": "admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_delete_admin_only(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "u@example.com")
    admin = await make_user(db_session, "a@example.com", role=Role.ADMIN)

    assert (await client.delete(f"/users/{user.id}", headers=auth_header(user))).status_code == 403
    resp = await client.delete(f"/users/{user.id}", headers=auth_header(admin))
    assert resp.status_code == 204


async def test_expired_or_garbage_token_unauthorized(client: AsyncClient) -> None:
    resp = await client.get("/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401
