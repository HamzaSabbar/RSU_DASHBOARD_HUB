from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from auth.deps import get_current_user
from config import settings
from data_platform.query import AnalyticsCatalogError, AnalyticsQueryService, cache_key
from data_platform.router import active_catalog, analytics_cache, etag_for_key
from data_platform.schemas import AnalyticsFilters
from db.models import User
from db.session import get_session

router = APIRouter(tags=["programmes-sociaux-rescoring"])


@router.get("/filters")
async def filters(
    response: Response,
    if_none_match: str | None = Header(default=None),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    release_key, database_path = await active_catalog(session)
    key = cache_key(release_key, "social-filters", {})
    etag = etag_for_key(key)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    payload = analytics_cache.get(key)
    cache_status = "HIT"
    if payload is None:
        cache_status = "MISS"
        try:
            payload = await run_in_threadpool(
                AnalyticsQueryService(
                    database_path, threads=min(settings.analytics_threads, 4)
                ).filter_options,
                release_key,
            )
        except AnalyticsCatalogError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        analytics_cache.set(key, payload)
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={"ETag": etag, "X-Analytics-Cache": cache_status},
    )


@router.get("/dashboard")
async def dashboard(
    filters: AnalyticsFilters = Depends(),
    if_none_match: str | None = Header(default=None),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    release_key, database_path = await active_catalog(session)
    key = cache_key(
        release_key,
        "social-dashboard",
        filters.model_dump(mode="json", exclude_none=True),
    )
    etag = etag_for_key(key)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    payload = analytics_cache.get(key)
    cache_status = "HIT"
    if payload is None:
        cache_status = "MISS"
        try:
            payload = await run_in_threadpool(
                AnalyticsQueryService(
                    database_path, threads=min(settings.analytics_threads, 4)
                ).social_programs_dashboard,
                release_key,
                filters,
            )
        except AnalyticsCatalogError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        analytics_cache.set(key, payload)
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={"ETag": etag, "X-Analytics-Cache": cache_status},
    )


@router.get("/cache")
async def board_cache_status(
    _user: User = Depends(get_current_user),
) -> dict[str, int]:
    return asdict(analytics_cache.stats())
