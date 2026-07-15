import uuid
from datetime import UTC, datetime, timedelta

from app.core import security
from app.core.config import settings
from app.core.email import EmailSender
from app.core.exceptions import (
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidVerificationCodeError,
)
from app.modules.auth.schemas import SignupRequest
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


async def signup(repo: UserRepository, data: SignupRequest, email_sender: EmailSender) -> User:
    email = data.email.lower()
    if await repo.get_by_email(email) is not None:
        raise EmailAlreadyExistsError

    code = security.generate_verification_code()
    user = User(
        email=email,
        hashed_password=security.hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        verification_code_hash=security.hash_verification_code(code),
        verification_code_expires_at=datetime.now(UTC)
        + timedelta(minutes=settings.verification_code_ttl_minutes),
    )
    repo.add(user)
    await repo.commit()
    # SIMPLIFICATION: sent synchronously after commit; with more time this would
    # be dispatched to a Celery queue with retries (and an outbox for atomicity).
    email_sender.send_verification_code(email, code)
    return user


async def verify(repo: UserRepository, email: str, code: str) -> User:
    user = await repo.get_by_email(email.lower())
    if user is None or user.is_verified or user.verification_code_hash is None:
        raise InvalidVerificationCodeError
    expires_at = user.verification_code_expires_at
    if expires_at is None or expires_at < datetime.now(UTC):
        raise InvalidVerificationCodeError
    if security.hash_verification_code(code) != user.verification_code_hash:
        raise InvalidVerificationCodeError

    user.is_verified = True
    user.verification_code_hash = None
    user.verification_code_expires_at = None
    await repo.commit()
    return user


async def login(repo: UserRepository, email: str, password: str) -> tuple[str, str]:
    user = await repo.get_by_email(email.lower())
    # Same error for unknown email and wrong password to avoid account enumeration.
    if user is None or not security.verify_password(password, user.hashed_password):
        raise InvalidCredentialsError
    if not user.is_verified:
        raise EmailNotVerifiedError
    return (
        security.create_access_token(user.id, user.role),
        security.create_refresh_token(user.id),
    )


async def refresh(repo: UserRepository, refresh_token: str) -> str:
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
    except security.TokenError as exc:
        raise InvalidCredentialsError from exc
    user = await repo.get_by_id(uuid.UUID(payload["sub"]))
    if user is None:
        raise InvalidCredentialsError
    return security.create_access_token(user.id, user.role)
