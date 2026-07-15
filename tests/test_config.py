from app.core.config import settings


def test_settings_defaults() -> None:
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.verification_code_ttl_minutes == 15
    assert settings.unverified_user_ttl_days == 2
    assert settings.database_url.startswith("postgresql+asyncpg://")
