from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    CoreDatasetVersion,
    DataProductBuild,
    DatasetArtifact,
    DatasetQualityCheck,
    DataSourceBatch,
    DataSourceFile,
    PlatformRelease,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


class DataPlatformRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_batch(
        self,
        *,
        source_key: str,
        source_path: Path,
        pipeline_version: str,
        parameters: dict[str, Any],
        created_by: uuid.UUID | None,
    ) -> DataSourceBatch:
        row = DataSourceBatch(
            source_key=source_key,
            source_path=str(source_path),
            pipeline_version=pipeline_version,
            parameters_json=parameters,
            status="queued",
            stage="queued",
            progress=0,
            created_by=created_by,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_batch(self, batch_id: uuid.UUID) -> DataSourceBatch | None:
        return await self.session.get(DataSourceBatch, batch_id)

    async def list_batches(self, limit: int = 50) -> list[DataSourceBatch]:
        rows = await self.session.scalars(
            select(DataSourceBatch).order_by(DataSourceBatch.created_at.desc()).limit(limit)
        )
        return list(rows)

    async def claim_next_queued(self) -> DataSourceBatch | None:
        row = await self.session.scalar(
            select(DataSourceBatch)
            .where(DataSourceBatch.status == "queued")
            .order_by(DataSourceBatch.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return None
        row.status = "running"
        row.stage = "inventory"
        row.progress = 5
        row.started_at = _now()
        row.error_summary = None
        await self.session.flush()
        return row

    async def update_batch(
        self,
        batch_id: uuid.UUID,
        *,
        stage: str | None = None,
        progress: int | None = None,
        content_hash: str | None = None,
    ) -> None:
        row = await self._require_batch(batch_id)
        if stage is not None:
            row.stage = stage
        if progress is not None:
            row.progress = max(0, min(100, progress))
        if content_hash is not None:
            row.content_hash = content_hash
        await self.session.flush()

    async def replace_source_files(
        self, batch_id: uuid.UUID, files: list[dict[str, Any]]
    ) -> None:
        await self.session.execute(delete(DataSourceFile).where(DataSourceFile.batch_id == batch_id))
        self.session.add_all([DataSourceFile(batch_id=batch_id, **item) for item in files])
        await self.session.flush()

    async def create_core_version(
        self,
        *,
        batch_id: uuid.UUID,
        version_key: str,
        dataset_path: Path,
        database_path: Path,
    ) -> CoreDatasetVersion:
        row = CoreDatasetVersion(
            batch_id=batch_id,
            version_key=version_key,
            status="building",
            dataset_path=str(dataset_path),
            database_path=str(database_path),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def complete_core_version(
        self,
        core_id: uuid.UUID,
        *,
        manifest_path: Path,
        row_counts: dict[str, int],
        period_start: Any,
        period_end: Any,
    ) -> None:
        row = await self.session.get(CoreDatasetVersion, core_id)
        if row is None:
            raise KeyError(f"core version {core_id} not found")
        row.status = "ready"
        row.manifest_path = str(manifest_path)
        row.row_counts_json = row_counts
        row.period_start = period_start
        row.period_end = period_end
        await self.session.flush()

    async def create_product_build(
        self,
        *,
        core_id: uuid.UUID,
        product_slug: str,
        product_version: str,
        artifact_path: Path,
        row_counts: dict[str, int],
    ) -> DataProductBuild:
        row = DataProductBuild(
            core_version_id=core_id,
            product_slug=product_slug,
            product_version=product_version,
            status="ready",
            artifact_path=str(artifact_path),
            row_counts_json=row_counts,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def replace_artifacts(
        self, core_id: uuid.UUID, artifacts: list[dict[str, Any]]
    ) -> None:
        await self.session.execute(
            delete(DatasetArtifact).where(DatasetArtifact.core_version_id == core_id)
        )
        self.session.add_all([DatasetArtifact(core_version_id=core_id, **item) for item in artifacts])
        await self.session.flush()

    async def replace_quality_checks(
        self,
        batch_id: uuid.UUID,
        core_id: uuid.UUID,
        checks: list[dict[str, Any]],
    ) -> None:
        await self.session.execute(
            delete(DatasetQualityCheck).where(DatasetQualityCheck.batch_id == batch_id)
        )
        self.session.add_all(
            [
                DatasetQualityCheck(batch_id=batch_id, core_version_id=core_id, **item)
                for item in checks
            ]
        )
        await self.session.flush()

    async def publish_release(
        self,
        *,
        core_id: uuid.UUID,
        release_key: str,
        products: dict[str, Any],
        published_by: uuid.UUID | None,
    ) -> PlatformRelease:
        now = _now()
        await self.session.execute(
            update(PlatformRelease)
            .where(PlatformRelease.is_active.is_(True))
            .values(is_active=False, superseded_at=now)
        )
        release = PlatformRelease(
            release_key=release_key,
            core_version_id=core_id,
            products_json=products,
            is_active=True,
            published_by=published_by,
            published_at=now,
        )
        self.session.add(release)
        await self.session.flush()
        return release

    async def mark_succeeded(self, batch_id: uuid.UUID) -> None:
        row = await self._require_batch(batch_id)
        row.status = "succeeded"
        row.stage = "published"
        row.progress = 100
        row.finished_at = _now()
        row.error_summary = None
        await self.session.flush()

    async def mark_failed(self, batch_id: uuid.UUID, message: str) -> None:
        row = await self._require_batch(batch_id)
        row.status = "failed"
        row.stage = "failed"
        row.finished_at = _now()
        row.error_summary = message[:10000]
        await self.session.flush()

    async def active_release(self) -> tuple[PlatformRelease, CoreDatasetVersion] | None:
        row = await self.session.execute(
            select(PlatformRelease, CoreDatasetVersion)
            .join(CoreDatasetVersion, CoreDatasetVersion.id == PlatformRelease.core_version_id)
            .where(PlatformRelease.is_active.is_(True), CoreDatasetVersion.status == "ready")
            .limit(1)
        )
        result = row.first()
        return (result[0], result[1]) if result else None

    async def batch_files(self, batch_id: uuid.UUID) -> list[DataSourceFile]:
        rows = await self.session.scalars(
            select(DataSourceFile)
            .where(DataSourceFile.batch_id == batch_id)
            .order_by(DataSourceFile.logical_name)
        )
        return list(rows)

    async def batch_checks(self, batch_id: uuid.UUID) -> list[DatasetQualityCheck]:
        rows = await self.session.scalars(
            select(DatasetQualityCheck)
            .where(DatasetQualityCheck.batch_id == batch_id)
            .order_by(DatasetQualityCheck.severity.desc(), DatasetQualityCheck.check_key)
        )
        return list(rows)

    async def core_for_batch(self, batch_id: uuid.UUID) -> CoreDatasetVersion | None:
        return cast(
            CoreDatasetVersion | None,
            await self.session.scalar(
                select(CoreDatasetVersion).where(CoreDatasetVersion.batch_id == batch_id)
            ),
        )

    async def release_for_core(self, core_id: uuid.UUID) -> PlatformRelease | None:
        return cast(
            PlatformRelease | None,
            await self.session.scalar(
                select(PlatformRelease)
                .where(PlatformRelease.core_version_id == core_id)
                .order_by(PlatformRelease.published_at.desc())
                .limit(1)
            ),
        )

    async def _require_batch(self, batch_id: uuid.UUID) -> DataSourceBatch:
        row = await self.session.get(DataSourceBatch, batch_id)
        if row is None:
            raise KeyError(f"data source batch {batch_id} not found")
        return row
