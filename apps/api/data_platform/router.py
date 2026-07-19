from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_report_manager, get_current_user
from config import settings
from data_platform.cache import VersionedResultCache
from data_platform.repository import DataPlatformRepository
from data_platform.schemas import (
    BatchDetailResponse,
    BatchResponse,
    BuildRequest,
    QualityCheckResponse,
    ReleaseResponse,
    SourceFileResponse,
)
from db.models import DataSourceBatch, User
from db.session import get_session

router = APIRouter(prefix="/api/data-platform", tags=["data-platform"])

analytics_cache = VersionedResultCache(
    ttl_seconds=settings.analytics_cache_ttl_seconds,
    max_entries=settings.analytics_cache_max_entries,
    max_bytes=settings.analytics_cache_max_bytes,
)


def _batch_response(row: DataSourceBatch) -> BatchResponse:
    return BatchResponse(
        id=str(row.id),
        source_key=row.source_key,
        pipeline_version=row.pipeline_version,
        content_hash=row.content_hash,
        status=row.status,
        stage=row.stage,
        progress=row.progress,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        error_summary=row.error_summary,
    )


@router.post("/batches", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_batch(
    request: BuildRequest,
    user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> BatchResponse:
    parameters = request.model_dump(mode="json")
    repository = DataPlatformRepository(session)
    row = await repository.create_batch(
        source_key=request.source_key,
        source_path=settings.analytics_source_path,
        pipeline_version=settings.analytics_pipeline_version,
        parameters=parameters,
        created_by=user.id,
    )
    await session.commit()
    return _batch_response(row)


@router.get("/batches", response_model=list[BatchResponse])
async def list_batches(
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BatchResponse]:
    return [
        _batch_response(row)
        for row in await DataPlatformRepository(session).list_batches(limit)
    ]


@router.get("/batches/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(
    batch_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BatchDetailResponse:
    repository = DataPlatformRepository(session)
    row = await repository.get_batch(batch_id)
    if row is None:
        raise HTTPException(status_code=404, detail="data source batch not found")
    files = await repository.batch_files(batch_id)
    checks = await repository.batch_checks(batch_id)
    core = await repository.core_for_batch(batch_id)
    release = await repository.release_for_core(core.id) if core else None
    return BatchDetailResponse(
        **_batch_response(row).model_dump(),
        files=[
            SourceFileResponse(
                logical_name=item.logical_name,
                relative_path=item.relative_path,
                sha256=item.sha256,
                byte_size=int(item.byte_size),
                row_count=int(item.row_count) if item.row_count is not None else None,
                required=item.required,
            )
            for item in files
        ],
        quality_checks=[
            QualityCheckResponse(
                check_key=item.check_key,
                severity=item.severity,
                passed=item.passed,
                observed_value=item.observed_value,
                expected_value=item.expected_value,
                details=item.details_json,
            )
            for item in checks
        ],
        core_version=core.version_key if core else None,
        release_key=release.release_key if release else None,
    )


@router.get("/releases/current", response_model=ReleaseResponse)
async def current_release(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReleaseResponse:
    active = await DataPlatformRepository(session).active_release()
    if active is None:
        raise HTTPException(status_code=404, detail="no published analytical release")
    release, core = active
    return ReleaseResponse(
        release_key=release.release_key,
        core_version=core.version_key,
        products=release.products_json,
        is_active=release.is_active,
        published_at=release.published_at,
        period_start=core.period_start,
        period_end=core.period_end,
    )


@router.get("/cache")
async def cache_status(_user: User = Depends(get_current_user)) -> dict[str, object]:
    return {
        **asdict(analytics_cache.stats()),
        "ttl_seconds": settings.analytics_cache_ttl_seconds,
        "max_entries": settings.analytics_cache_max_entries,
        "max_bytes": settings.analytics_cache_max_bytes,
        "policy": "release-versioned TTL/LRU; compact aggregate responses only",
    }


def etag_for_key(key: str) -> str:
    return f'"{hashlib.sha256(key.encode()).hexdigest()}"'


async def active_catalog(
    session: AsyncSession,
) -> tuple[str, Path]:
    active = await DataPlatformRepository(session).active_release()
    if active is None:
        raise HTTPException(status_code=404, detail="no published analytical release")
    release, core = active
    path = Path(core.database_path)
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail="published analytical catalog is not mounted in the API service",
        )
    return release.release_key, path
