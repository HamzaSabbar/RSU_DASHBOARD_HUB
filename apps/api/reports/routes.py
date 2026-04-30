from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from db.models import User
from db.session import get_session
from reports import service
from reports.schemas import ReportJobCreateResponse, ReportJobStatusResponse, ValidationResult

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/jobs", response_model=ReportJobCreateResponse)
async def create_job(
    file: UploadFile = File(...),
    replace: bool = Query(default=False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportJobCreateResponse:
    response = await service.create_report_job(
        session,
        upload=file,
        replace=replace,
        created_by=str(user.id),
    )
    return response


@router.get("/latest/status", response_model=ReportJobStatusResponse)
async def latest_job_status(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportJobStatusResponse:
    repo = service.repository_for_session(session)
    return await service.get_latest_job_status(repo)


@router.get("/latest/validation", response_model=ValidationResult)
async def latest_job_validation(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ValidationResult:
    repo = service.repository_for_session(session)
    return await service.get_latest_validation_result(repo)


@router.get("/latest/dashboard")
async def latest_job_dashboard(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = service.repository_for_session(session)
    return await service.get_latest_dashboard_json(repo)


@router.get("/dashboard")
async def dashboard_for_range(
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await service.get_dashboard_for_range(
        session,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/available-periods")
async def available_periods(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await service.get_available_periods(session)


@router.get("/jobs/{job_id}/status", response_model=ReportJobStatusResponse)
async def job_status(
    job_id: str,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportJobStatusResponse:
    repo = service.repository_for_session(session)
    return await service.get_job_status(repo, job_id)


@router.get("/jobs/{job_id}/validation", response_model=ValidationResult)
async def job_validation(
    job_id: str,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ValidationResult:
    repo = service.repository_for_session(session)
    return await service.get_validation_result(repo, job_id)


@router.get("/jobs/{job_id}/dashboard")
async def job_dashboard(
    job_id: str,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = service.repository_for_session(session)
    return await service.get_dashboard_json(repo, job_id)
