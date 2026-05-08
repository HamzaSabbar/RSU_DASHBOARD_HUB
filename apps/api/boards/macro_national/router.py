from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_report_manager, get_current_user
from boards.macro_national import service
from boards.macro_national.schemas import MacroNationalPayload
from db.models import User
from db.session import get_session

router = APIRouter(tags=["macro-national"])


class UploadResult(BaseModel):
    filename: str
    file_kind: str
    status: str
    row_count: int | None
    error: str | None = None


class UploadSummary(BaseModel):
    files_accepted: list[UploadResult]
    files_rejected: list[UploadResult]


@router.get("/data", response_model=MacroNationalPayload)
async def get_data(
    reporting_date: date | None = Query(default=None),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MacroNationalPayload:
    return await service.get_latest_payload(session, on_or_before=reporting_date)


@router.post("/upload", response_model=UploadSummary)
async def upload(
    files: list[UploadFile],
    user: User = Depends(get_current_report_manager),
    session: AsyncSession = Depends(get_session),
) -> UploadSummary:
    accepted: list[UploadResult] = []
    rejected: list[UploadResult] = []

    for file in files:
        content = await file.read()
        row, err = await service.persist_upload(
            session,
            user=user,
            original_filename=file.filename or "uploaded.xlsx",
            content=content,
        )
        bucket = rejected if err else accepted
        bucket.append(
            UploadResult(
                filename=row.original_filename,
                file_kind=row.file_kind,
                status=row.status,
                row_count=row.row_count,
                error=err,
            )
        )

    if accepted:
        await service.recompute_snapshot(session, user=user)

    await session.commit()
    return UploadSummary(files_accepted=accepted, files_rejected=rejected)
