from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Users API"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/users"
    redis_url: str = "redis://localhost:6379/0"

    # SIMPLIFICATION: default secret lets dev/tests run without a .env; in production,
    # fail hard at startup if this default is detected.
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    verification_code_ttl_minutes: int = 15
    unverified_user_ttl_days: int = 2


settings = Settings()
