from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_admin_user, get_current_report_manager, get_current_user
from db.models import (
    AuditLog,
    BoardSnapshot,
    ReportAmountRuleFact,
    ReportCodeFact,
    ReportFmsBlockedFact,
    ReportFmsTreatmentFact,
    ReportJob,
    ReportProgramFlowFact,
    ReportProgramFraudFact,
    ReportProgramRescoringFact,
    ReportProgramStockFact,
    ReportProvinceFact,
    ReportRegionFact,
    ReportRsuAnnotationFact,
    ReportRsuFlowFact,
    ReportRsuStockFact,
    ReportUploadBatch,
    Upload,
    User,
)
from db.session import get_session
from reports import service, template
from reports.schemas import ReportJobCreateResponse, ReportJobStatusResponse, ValidationResult

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORT_FACT_MODELS = (
    ReportAmountRuleFact,
    ReportFmsBlockedFact,
    ReportFmsTreatmentFact,
    ReportProgramFraudFact,
    ReportProgramRescoringFact,
    ReportProgramFlowFact,
    ReportProgramStockFact,
    ReportRsuAnnotationFact,
    ReportRsuFlowFact,
    ReportRsuStockFact,
    ReportCodeFact,
    ReportProvinceFact,
    ReportRegionFact,
)


async def _count_rows(session: AsyncSession, model: type[Any]) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


@router.post("/jobs", response_model=ReportJobCreateResponse)
async def create_job(
    file: UploadFile = File(...),
    replace: bool = Query(default=False),
    user: User = Depends(get_current_report_manager),
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
    _user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> ReportJobStatusResponse:
    repo = service.repository_for_session(session)
    return await service.get_latest_job_status(repo)


@router.get("/latest/validation", response_model=ValidationResult)
async def latest_job_validation(
    _user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> ValidationResult:
    repo = service.repository_for_session(session)
    return await service.get_latest_validation_result(repo)


@router.get("/latest/dashboard")
async def latest_job_dashboard(
    _user: User = Depends(get_current_report_manager),
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


@router.get("/template.xlsx")
async def excel_template(
    _user: User = Depends(get_current_report_manager),
) -> Response:
    return Response(
        content=template.build_excel_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="rsu-dashboard-template.xlsx"',
        },
    )


@router.get("/jobs/{job_id}/status", response_model=ReportJobStatusResponse)
async def job_status(
    job_id: str,
    _user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> ReportJobStatusResponse:
    repo = service.repository_for_session(session)
    return await service.get_job_status(repo, job_id)


@router.get("/jobs/{job_id}/validation", response_model=ValidationResult)
async def job_validation(
    job_id: str,
    _user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> ValidationResult:
    repo = service.repository_for_session(session)
    return await service.get_validation_result(repo, job_id)


@router.get("/jobs/{job_id}/dashboard")
async def job_dashboard(
    job_id: str,
    _user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    repo = service.repository_for_session(session)
    return await service.get_dashboard_json(repo, job_id)


@router.delete("/admin/data")
async def clear_report_data(
    user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    counts: dict[str, int] = {
        "reportJobs": await _count_rows(session, ReportJob),
        "uploadBatches": await _count_rows(session, ReportUploadBatch),
        "legacyUploads": await _count_rows(session, Upload),
        "boardSnapshots": await _count_rows(session, BoardSnapshot),
    }
    counts["factRows"] = sum(
        [await _count_rows(session, model) for model in REPORT_FACT_MODELS]
    )

    for model in REPORT_FACT_MODELS:
        await session.execute(delete(model))
    await session.execute(update(ReportUploadBatch).values(superseded_by_batch_id=None))
    await session.execute(delete(ReportUploadBatch))
    await session.execute(delete(ReportJob))
    await session.execute(delete(BoardSnapshot))
    await session.execute(delete(Upload))
    session.add(
        AuditLog(
            user_id=user.id,
            action="clear_report_data",
            target_type="reports",
            target_id=None,
            audit_metadata=counts,
        )
    )
    await session.commit()
    return {"status": "cleared", "deleted": counts}
