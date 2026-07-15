import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.modules.users.models import Role

_password_hasher = PasswordHash.recommended()


class TokenError(Exception):
    """Raised when a JWT is invalid, expired, or of the wrong type."""


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hasher.verify(password, hashed)


def generate_verification_code() -> str:
    """Return a 6-digit numeric verification code."""
    return f"{secrets.randbelow(10**6):06d}"


def hash_verification_code(code: str) -> str:
    # SIMPLIFICATION: sha256 without salt is acceptable for short-lived 6-digit
    # codes; with more time, store salted hashes plus an attempt counter to
    # throttle brute force.
    return hashlib.sha256(code.encode()).hexdigest()


def _create_token(subject: uuid.UUID, token_type: str, lifetime: timedelta, **extra: Any) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(subject), "type": token_type, "iat": now, "exp": now + lifetime, **extra}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, role: Role) -> str:
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(user_id, "access", lifetime, role=role.value)


def create_refresh_token(user_id: uuid.UUID) -> str:
    # SIMPLIFICATION: refresh tokens are stateless JWTs. With more time, persist
    # a jti per token family to support rotation and server-side revocation.
    lifetime = timedelta(days=settings.refresh_token_expire_days)
    return _create_token(user_id, "refresh", lifetime)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"Expected {expected_type} token")
    return payload
