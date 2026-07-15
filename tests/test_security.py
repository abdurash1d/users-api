import uuid

import pytest

from app.core import security
from app.modules.users.models import Role


def test_password_hash_roundtrip() -> None:
    hashed = security.hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert security.verify_password("s3cret-pass", hashed)
    assert not security.verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id, Role.ADMIN)
    payload = security.decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"


def test_refresh_token_rejected_as_access() -> None:
    token = security.create_refresh_token(uuid.uuid4())
    with pytest.raises(security.TokenError):
        security.decode_token(token, expected_type="access")


def test_garbage_token_rejected() -> None:
    with pytest.raises(security.TokenError):
        security.decode_token("not-a-jwt", expected_type="access")
