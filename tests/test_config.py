import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


def test_settings_defaults() -> None:
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.verification_code_ttl_minutes == 15
    assert settings.unverified_user_ttl_days == 2
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_settings_ignore_unprefixed_debug_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.delenv("USERS_API_DEBUG", raising=False)

    configured = Settings(
        _env_file=None,
        jwt_secret_key="tests-only-signing-key-at-least-32-bytes",
    )

    assert configured.debug is False


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_settings_require_explicit_strong_jwt_secret(
    monkeypatch: pytest.MonkeyPatch, secret: str | None
) -> None:
    monkeypatch.delenv("USERS_API_JWT_SECRET_KEY", raising=False)
    kwargs = {} if secret is None else {"jwt_secret_key": secret}

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **kwargs)
