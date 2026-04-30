from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.session import SessionLocal
from reports import calculations, facts, parser
from reports.repository import (
    LocalJsonReportJobRepository,
    ReportJobRecord,
    ReportJobRepository,
    SqlAlchemyReportJobRepository,
)
from reports.schemas import (
    DashboardJson,
    ReportJobCreateResponse,
    ReportJobStatusResponse,
    ValidationMessage,
    ValidationResult,
    ValidationSummary,
)
from reports.storage import build_object_path, get_storage

logger = logging.getLogger("uvicorn.error")

_LOCAL_REPOSITORY = LocalJsonReportJobRepository(
    Path(settings.storage_local_path) / "report_jobs.json"
)


def repository_for_session(session: AsyncSession | None = None) -> ReportJobRepository:
    if settings.report_job_repository.lower() == "local":
        return _LOCAL_REPOSITORY
    if session is None:
        raise RuntimeError("Session SQLAlchemy requise pour report_job_repository=db")
    return SqlAlchemyReportJobRepository(session)


async def create_report_job(
    session: AsyncSession,
    *,
    upload: UploadFile,
    replace: bool,
    created_by: str | None,
) -> ReportJobCreateResponse:
    filename = upload.filename or "input.xlsx"
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers .xlsx sont acceptés.",
        )
    content = await upload.read()
    max_bytes = settings.report_max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux: limite {settings.report_max_upload_size_mb} Mo.",
        )
    if not content.startswith(b"PK"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FICHIER_XLSX_INVALIDE",
                "message": "Type de fichier non reconnu: un fichier .xlsx valide est attendu.",
            },
        )

    client_id_chargement = parser.extract_id_chargement(content)
    repo = repository_for_session(session)
    if client_id_chargement and not replace:
        if settings.report_job_repository.lower() == "db" and await facts.active_batch_exists(
            session, client_id_chargement
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_ID_CHARGEMENT",
                    "idChargement": client_id_chargement,
                    "message": (
                        "Un chargement avec cet id_chargement existe déjà. "
                        "Confirmez le remplacement pour écraser la version active."
                    ),
                },
            )
        existing = await repo.find_latest_by_business_id(client_id_chargement)
        if existing and existing.status in {"queued", "running", "succeeded"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_ID_CHARGEMENT",
                    "idChargement": client_id_chargement,
                    "message": (
                        "Un chargement avec cet id_chargement existe déjà. "
                        "Confirmez le remplacement pour écraser la version active."
                    ),
                },
            )

    job_id = str(uuid.uuid4())
    id_chargement = client_id_chargement or f"JOB_{job_id}"
    raw_object_path = build_object_path("uploads", job_id, "input.xlsx")
    get_storage().put_bytes(raw_object_path, content)
    await repo.create(
        job_id=job_id,
        id_chargement=id_chargement,
        original_filename=filename,
        raw_object_path=raw_object_path,
        replace_requested=replace,
        created_by=created_by,
    )
    if settings.report_job_repository.lower() == "db":
        await session.commit()

    return ReportJobCreateResponse(
        job_id=job_id,
        status="queued",
        status_url=f"/api/reports/jobs/{job_id}/status",
        dashboard_url=f"/api/reports/jobs/{job_id}/dashboard",
        validation_url=f"/api/reports/jobs/{job_id}/validation",
    )


async def process_report_job(job_id: str) -> None:
    if settings.report_job_repository.lower() == "local":
        await _process_with_repository(
            job_id,
            _LOCAL_REPOSITORY,
            commit=None,
            mark_running=True,
            session=None,
        )
        return

    async with SessionLocal() as session:
        repo = SqlAlchemyReportJobRepository(session)

        async def commit() -> None:
            await session.commit()

        await _process_with_repository(
            job_id,
            repo,
            commit=commit,
            mark_running=True,
            session=session,
        )


async def process_next_report_job() -> bool:
    if settings.report_job_repository.lower() == "local":
        record = await _LOCAL_REPOSITORY.claim_next_queued()
        if record is None:
            return False
        await _process_with_repository(
            record.id,
            _LOCAL_REPOSITORY,
            commit=None,
            mark_running=False,
            session=None,
        )
        return True

    async with SessionLocal() as session:
        repo = SqlAlchemyReportJobRepository(session)
        record = await repo.claim_next_queued()
        await session.commit()
        if record is None:
            return False

        async def commit() -> None:
            await session.commit()

        await _process_with_repository(
            record.id,
            repo,
            commit=commit,
            mark_running=False,
            session=session,
        )
        return True


async def _process_with_repository(
    job_id: str,
    repo: ReportJobRepository,
    *,
    commit: Any,
    mark_running: bool,
    session: AsyncSession | None,
) -> None:
    storage_client = get_storage()
    try:
        if mark_running:
            await repo.mark_running(job_id)
            if commit:
                await commit()

        record = await _require_job(repo, job_id)
        raw = storage_client.get_bytes(record.raw_object_path)
        await repo.update_progress(job_id, 25)
        if commit:
            await commit()

        parsed = parser.parse_workbook(raw, job_id=job_id)
        _apply_server_upload_id(parsed, record.id_chargement)
        normalized_path = build_object_path("jobs", job_id, "normalized.json")
        validation_path = build_object_path("jobs", job_id, "validation.json")
        storage_client.put_json(normalized_path, parsed.normalized)
        storage_client.put_json(
            validation_path,
            parsed.validation.model_dump(mode="json", by_alias=True),
        )
        await repo.attach_artifacts(
            job_id,
            normalized_object_path=normalized_path,
            validation_object_path=validation_path,
        )
        await repo.update_progress(job_id, 60)
        if commit:
            await commit()

        if parsed.validation.has_errors:
            await repo.mark_failed(
                job_id,
                f"Validation échouée: {parsed.validation.summary.errors} erreur(s).",
            )
            if commit:
                await commit()
            return

        dashboard = calculations.build_dashboard(
            parsed.normalized,
            job_id=job_id,
            validation=parsed.validation,
        )
        dashboard_path = build_object_path("jobs", job_id, "dashboard.json")
        storage_client.put_json(dashboard_path, dashboard)
        await repo.attach_artifacts(job_id, dashboard_object_path=dashboard_path)
        await repo.update_progress(job_id, 90)
        if session is not None and settings.report_job_repository.lower() == "db":
            record = await _require_job(repo, job_id)
            await facts.ingest_report_batch(
                session,
                record=record,
                normalized=parsed.normalized,
            )
        await repo.mark_succeeded(job_id)
        if commit:
            await commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Report job %s failed", job_id)
        try:
            if session is not None:
                await session.rollback()
            await repo.mark_failed(job_id, f"Erreur de traitement: {exc}")
            if commit:
                await commit()
        except Exception:  # noqa: BLE001
            logger.exception("Could not mark report job %s as failed", job_id)


def _apply_server_upload_id(
    parsed: parser.ParsedWorkbook,
    id_chargement: str | None,
) -> None:
    if not id_chargement:
        return
    metadata = parsed.normalized.setdefault("metadata", {})
    if isinstance(metadata, dict) and not metadata.get("id_chargement"):
        metadata["id_chargement"] = id_chargement
    parsed.validation.id_chargement = id_chargement


async def get_job_status(
    repo: ReportJobRepository,
    job_id: str,
) -> ReportJobStatusResponse:
    record = await _require_job(repo, job_id)
    return _status_response(record)


async def get_validation_result(
    repo: ReportJobRepository,
    job_id: str,
) -> ValidationResult:
    record = await _require_job(repo, job_id)
    if record.validation_object_path:
        return ValidationResult.model_validate(get_storage().get_json(record.validation_object_path))
    if record.error_summary:
        return ValidationResult(
            job_id=job_id,
            id_chargement=record.id_chargement,
            summary=ValidationSummary(errors=1),
            messages=[
                ValidationMessage(
                    severity="error",
                    code="TRAITEMENT_ECHOUE",
                    message=record.error_summary,
                )
            ],
        )
    return ValidationResult(job_id=job_id, id_chargement=record.id_chargement)


async def get_dashboard_json(
    repo: ReportJobRepository,
    job_id: str,
) -> DashboardJson:
    record = await _require_job(repo, job_id)
    if record.status != "succeeded":
        message = {
            "queued": "Le traitement du rapport est en attente.",
            "running": "Le traitement du rapport est en cours.",
            "failed": record.error_summary or "Le traitement du rapport a échoué.",
        }.get(record.status, "Le rapport n’est pas disponible.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "jobId": job_id,
                "status": record.status,
                "message": message,
                "validationUrl": f"/api/reports/jobs/{job_id}/validation",
            },
        )
    if not record.dashboard_object_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard JSON introuvable pour ce job.",
        )
    return get_storage().get_json(record.dashboard_object_path)


async def get_latest_job_status(repo: ReportJobRepository) -> ReportJobStatusResponse:
    record = await repo.find_latest_succeeded()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport traité disponible.",
        )
    return _status_response(record)


async def get_latest_dashboard_json(repo: ReportJobRepository) -> DashboardJson:
    record = await repo.find_latest_succeeded()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport traité disponible.",
        )
    return await get_dashboard_json(repo, record.id)


async def get_dashboard_for_range(
    session: AsyncSession,
    *,
    start_date: date | None,
    end_date: date | None,
) -> DashboardJson:
    return await facts.build_dashboard_for_range(
        session,
        start_date=start_date,
        end_date=end_date,
    )


async def get_available_periods(session: AsyncSession) -> dict[str, Any]:
    return await facts.available_periods(session)


async def get_latest_validation_result(repo: ReportJobRepository) -> ValidationResult:
    record = await repo.find_latest_succeeded()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport traité disponible.",
        )
    return await get_validation_result(repo, record.id)


async def _require_job(
    repo: ReportJobRepository,
    job_id: str,
) -> ReportJobRecord:
    record = await repo.get(job_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job introuvable: {job_id}",
        )
    return record


def _status_response(record: ReportJobRecord) -> ReportJobStatusResponse:
    return ReportJobStatusResponse(
        job_id=record.id,
        status=record.status,
        progress=record.progress,
        created_at=record.created_at or datetime.now(tz=UTC),
        started_at=record.started_at,
        finished_at=record.finished_at,
        error_summary=record.error_summary,
    )
