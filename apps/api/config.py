from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rsu:change-me-in-prod@db:5432/rsu_dashboard"
    database_url_sync: str = "postgresql+psycopg://rsu:change-me-in-prod@db:5432/rsu_dashboard"
    nextauth_secret: str = "replace-me"
    web_origin: str = "http://localhost:3100"
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

    # Platform-wide RSU analytical plane. The API only reads published releases;
    # the analytics worker owns all writes below this directory.
    analytics_source_path: Path = Path("/data/rsu-source")
    analytics_local_path: Path = Path("/data/analytics")
    analytics_pipeline_version: str = "rsu-duckdb-v1"
    analytics_memory_limit: str = "4GB"
    analytics_threads: int = 4
    analytics_temp_directory: Path = Path("/data/analytics/tmp")
    analytics_max_temp_directory_size: str = "20GB"
    analytics_worker_poll_seconds: float = 2.0
    analytics_cache_ttl_seconds: int = 900
    analytics_cache_max_entries: int = 512
    analytics_cache_max_bytes: int = 64 * 1024 * 1024
    analytics_query_timeout_seconds: int = 60


settings = Settings()
