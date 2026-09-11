from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rsu:change-me-in-prod@db:5432/rsu_dashboard"
    database_url_sync: str = "postgresql+psycopg://rsu:change-me-in-prod@db:5432/rsu_dashboard"
    nextauth_secret: str = "replace-me"
    web_origin: str = "http://localhost:3100"
    admin_email: str = "admin@rsu.local"
    admin_password: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 60 * 60 * 8  # 8h


settings = Settings()
