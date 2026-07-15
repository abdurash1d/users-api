from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.modules.users.models import User
from tests.conftest import RecordingEmailSender

SIGNUP = {"email": "Alice@Example.com", "password": "password123", "first_name": "Alice"}


async def signup_and_verify(client: AsyncClient, sender: RecordingEmailSender) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    code = sender.codes["alice@example.com"]
    resp = await client.post("/auth/verify", json={"email": "alice@example.com", "code": code})
    assert resp.status_code == 200


async def test_signup_creates_unverified_user(client, email_sender) -> None:
    resp = await client.post("/auth/signup", json=SIGNUP)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"  # normalized to lowercase
    assert body["is_verified"] is False
    assert body["role"] == "user"
    assert "hashed_password" not in body
    assert "alice@example.com" in email_sender.codes


async def test_signup_duplicate_email_conflict(client, email_sender) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    resp = await client.post("/auth/signup", json={**SIGNUP, "email": "ALICE@example.com"})
    assert resp.status_code == 409


async def test_verify_with_wrong_code(client, email_sender) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    resp = await client.post("/auth/verify", json={"email": "alice@example.com", "code": "000000"})
    assert resp.status_code == 400


async def test_login_before_verification_forbidden(client, email_sender) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert resp.status_code == 403


async def test_full_flow_signup_verify_login_refresh(client, email_sender) -> None:
    await signup_and_verify(client, email_sender)

    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert tokens["token_type"] == "bearer"

    resp = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_login_wrong_password(client, email_sender) -> None:
    await signup_and_verify(client, email_sender)
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_refresh_rejects_access_token(client, email_sender) -> None:
    await signup_and_verify(client, email_sender)
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    resp = await client.post("/auth/refresh", json={"refresh_token": resp.json()["access_token"]})
    assert resp.status_code == 401


async def test_verify_expired_code(client, email_sender, db_session) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    code = email_sender.codes["alice@example.com"]
    await db_session.execute(
        update(User)
        .where(User.email == "alice@example.com")
        .values(verification_code_expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    await db_session.commit()
    resp = await client.post("/auth/verify", json={"email": "alice@example.com", "code": code})
    assert resp.status_code == 400


async def test_verify_already_verified_user(client, email_sender) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    code = email_sender.codes["alice@example.com"]
    await client.post("/auth/verify", json={"email": "alice@example.com", "code": code})
    resp = await client.post("/auth/verify", json={"email": "alice@example.com", "code": code})
    assert resp.status_code == 400


async def test_refresh_garbage_token(client) -> None:
    resp = await client.post("/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401


async def test_refresh_rejected_after_deverification(client, email_sender, db_session) -> None:
    await signup_and_verify(client, email_sender)
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    refresh_token = resp.json()["refresh_token"]

    await db_session.execute(
        update(User).where(User.email == "alice@example.com").values(is_verified=False)
    )
    await db_session.commit()

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 403
