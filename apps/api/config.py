from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rsu:change-me-in-prod@db:5432/rsu_dashboard"
    database_url_sync: str = "postgresql+psycopg://rsu:change-me-in-prod@db:5432/rsu_dashboard"
    nextauth_secret: str = "replace-me"
    admin_email: str = "admin@rsu.local"
    admin_password: str = "change-me-in-prod"
    upload_dir: Path = Path("/data/uploads")
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 60 * 60 * 8  # 8h
    gcs_bucket_name: str | None = None
    gcs_prefix: str = "rsu-dashboard"
    storage_driver: str = "local"
    storage_local_path: Path = Path("./storage")
    report_max_upload_size_mb: int = 50
    report_job_repository: str = "db"
    report_worker_poll_seconds: float = 2.0


settings = Settings()
