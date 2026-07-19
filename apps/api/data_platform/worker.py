from __future__ import annotations

import asyncio
import logging
import uuid

from config import settings
from data_platform.pipeline import RsuCsvPipeline
from data_platform.repository import DataPlatformRepository
from db.models import AuditLog
from db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-platform.worker")


async def _claim() -> tuple[uuid.UUID, uuid.UUID | None, dict[str, object]] | None:
    async with SessionLocal() as session, session.begin():
        batch = await DataPlatformRepository(session).claim_next_queued()
        if batch is None:
            return None
        return batch.id, batch.created_by, dict(batch.parameters_json)


async def _set_stage(batch_id: uuid.UUID, stage: str, progress: int) -> None:
    async with SessionLocal() as session, session.begin():
        await DataPlatformRepository(session).update_batch(
            batch_id, stage=stage, progress=progress
        )


async def _persist_success(
    batch_id: uuid.UUID,
    created_by: uuid.UUID | None,
    result: object,
) -> None:
    from data_platform.pipeline import BuildResult

    if not isinstance(result, BuildResult):
        raise TypeError("pipeline returned an unexpected result")
    async with SessionLocal() as session, session.begin():
        repository = DataPlatformRepository(session)
        await repository.update_batch(
            batch_id,
            stage="publishing",
            progress=90,
            content_hash=result.content_hash,
        )
        await repository.replace_source_files(batch_id, result.source_files)
        core = await repository.create_core_version(
            batch_id=batch_id,
            version_key=result.version_key,
            dataset_path=result.dataset_path,
            database_path=result.database_path,
        )
        product = await repository.create_product_build(
            core_id=core.id,
            product_slug="programmes-sociaux-rescoring",
            product_version="programmes-sociaux-rescoring-v1",
            artifact_path=result.dataset_path / "products" / "programmes-sociaux-rescoring",
            row_counts={
                key: value
                for key, value in result.row_counts.items()
                if key.startswith("mart_") or key == "fact_program_crossing"
            },
        )
        artifacts = []
        for artifact in result.artifacts:
            item = dict(artifact)
            if item["layer"] == "product":
                item["product_build_id"] = product.id
            artifacts.append(item)
        await repository.replace_artifacts(core.id, artifacts)
        await repository.replace_quality_checks(
            batch_id, core.id, result.quality_checks
        )
        await repository.complete_core_version(
            core.id,
            manifest_path=result.manifest_path,
            row_counts=result.row_counts,
            period_start=result.period_start,
            period_end=result.period_end,
        )
        release = await repository.publish_release(
            core_id=core.id,
            release_key=result.version_key,
            products=result.products,
            published_by=created_by,
        )
        session.add(
            AuditLog(
                user_id=created_by,
                action="data_platform.release_published",
                target_type="platform_release",
                target_id=release.id,
                audit_metadata={
                    "batch_id": str(batch_id),
                    "release_key": result.version_key,
                    "content_hash": result.content_hash,
                },
            )
        )
        await repository.mark_succeeded(batch_id)


async def _mark_failed(batch_id: uuid.UUID, exc: Exception) -> None:
    logger.exception("Analytics build %s failed", batch_id, exc_info=exc)
    async with SessionLocal() as session, session.begin():
        await DataPlatformRepository(session).mark_failed(batch_id, str(exc))


async def process_one() -> bool:
    claimed = await _claim()
    if claimed is None:
        return False
    batch_id, created_by, parameters = claimed
    try:
        await _set_stage(batch_id, "hashing-and-transforming", 15)
        pipeline = RsuCsvPipeline(
            source_path=settings.analytics_source_path,
            analytics_path=settings.analytics_local_path,
            pipeline_version=settings.analytics_pipeline_version,
            memory_limit=settings.analytics_memory_limit,
            threads=settings.analytics_threads,
            temp_directory=settings.analytics_temp_directory,
            max_temp_directory_size=settings.analytics_max_temp_directory_size,
            include_score_variables=bool(parameters.get("include_score_variables", True)),
        )
        result = await asyncio.to_thread(pipeline.build, str(batch_id))
        await _persist_success(batch_id, created_by, result)
        logger.info("Published analytics release %s", result.version_key)
    except Exception as exc:
        await _mark_failed(batch_id, exc)
    return True


async def run_forever() -> None:
    logger.info("Data platform worker started")
    while True:
        processed = await process_one()
        if not processed:
            await asyncio.sleep(settings.analytics_worker_poll_seconds)


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
