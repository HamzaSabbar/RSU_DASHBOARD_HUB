"""`/api/kpi/*` — one static router for the fixed set of 18 KPIs.

Unlike `boards/router.py`'s dynamic per-board mounting, this product ships a
fixed KPI catalog rather than pluggable boards, so a single static router is
more honest than reusing the board discovery/mount pattern.

Route order matters: literal paths (`/filters`, `/overview`, `/imports`, ...)
must be registered before the `/{code}` catch-all, or FastAPI would match
e.g. `GET /api/kpi/imports` to `GET /{code}` with `code="imports"` first.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_report_manager, get_current_user
from db.models import User
from db.session import get_session
from kpi import importer, service
from kpi.registry import GLOBAL_DIMENSIONS, SECTIONS, discover_kpis, kpis_in_section

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


def _global_filters(
    start_date: date | None,
    end_date: date | None,
    region: str | None,
    province: str | None,
    milieu: str | None,
) -> dict[str, object]:
    return {
        "period_start": start_date,
        "period_end": end_date,
        "region": region,
        "province": province,
        "milieu": milieu,
    }


def _card_to_dict(card: service.KpiCard) -> dict[str, Any]:
    return dataclasses.asdict(card)


def _preview_to_dict(preview: importer.ImportPreview) -> dict[str, Any]:
    return dataclasses.asdict(preview)


@router.get("/filters")
async def get_filters(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await service.get_filter_options(session)


@router.get("/overview")
async def get_overview(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    province: str | None = Query(default=None),
    milieu: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    filters = _global_filters(start_date, end_date, region, province, milieu)
    cards = await service.compute_overview(session, filters)
    return {"cards": [_card_to_dict(c) for c in cards]}


@router.get("/sections/{section}")
async def get_section(
    section: str,
    request: Request,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    province: str | None = Query(default=None),
    milieu: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if section not in SECTIONS:
        raise HTTPException(status_code=404, detail="section inconnue")
    base_filters = _global_filters(start_date, end_date, region, province, milieu)
    specs = kpis_in_section(section)
    cards = []
    for spec in specs:
        filters = dict(base_filters)
        prefix = f"{spec.code}."
        for key, value in request.query_params.items():
            if key.startswith(prefix):
                filters[key[len(prefix) :]] = value
        card = await service.compute_kpi_card(session, spec, filters)
        if spec.default_breakdown:
            card.default_breakdown_dimension = spec.default_breakdown
            card.default_breakdown_items = await service.compute_breakdown(
                session, spec, filters, spec.default_breakdown
            )
        cards.append(_card_to_dict(card))
    return {"section": section, "title": SECTIONS[section], "cards": cards}


@router.post("/imports/validate")
async def validate_import(
    file: UploadFile,
    mode: str | None = Query(default=None),
    _user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    content = await file.read()
    resolved_mode = await service.resolve_import_mode(session, mode)
    preview = await importer.validate_workbook(
        session,
        file_bytes=content,
        filename=file.filename or "upload.xlsx",
        mode=resolved_mode,
    )
    return _preview_to_dict(preview)


@router.post("/imports")
async def commit_import(
    file: UploadFile,
    mode: str | None = Query(default=None),
    user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    content = await file.read()
    resolved_mode = await service.resolve_import_mode(session, mode)
    preview = await importer.commit_workbook(
        session,
        file_bytes=content,
        filename=file.filename or "upload.xlsx",
        mode=resolved_mode,
        uploaded_by=user.id,
    )
    if not preview.valid and not preview.already_committed:
        raise HTTPException(status_code=422, detail=_preview_to_dict(preview))
    if preview.valid and not preview.already_committed:
        service.invalidate_filter_options_cache()
    return _preview_to_dict(preview)


@router.get("/imports")
async def get_imports(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rows = await service.list_imports(session, limit=limit, offset=offset)
    return {
        "imports": [
            {
                "id": str(r.id),
                "filename": r.filename,
                "checksum": r.checksum,
                "uploaded_at": r.uploaded_at,
                "mode": r.mode,
                "status": r.status,
                "recognized_sheets": r.recognized_sheets,
                "missing_sheets": r.missing_sheets,
                "unknown_sheets": r.unknown_sheets,
                "row_counts": r.row_counts,
                "period_min": r.period_min,
                "period_max": r.period_max,
                "committed_at": r.committed_at,
            }
            for r in rows
        ]
    }


@router.get("/{code}")
async def get_kpi(
    code: str,
    request: Request,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    province: str | None = Query(default=None),
    milieu: str | None = Query(default=None),
    breakdown: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    registry = discover_kpis()
    spec = registry.get(code)
    if spec is None:
        raise HTTPException(status_code=404, detail="KPI inconnu")

    filters = _global_filters(start_date, end_date, region, province, milieu)
    for key, value in request.query_params.items():
        if key in spec.supported_filters and key not in GLOBAL_DIMENSIONS:
            filters[key] = value

    card = await service.compute_kpi_card(session, spec, filters)
    result: dict[str, Any] = {"kpi": _card_to_dict(card)}
    if breakdown:
        result["breakdown"] = {
            "dimension": breakdown,
            "items": await service.compute_breakdown(session, spec, filters, breakdown),
        }
    return result
