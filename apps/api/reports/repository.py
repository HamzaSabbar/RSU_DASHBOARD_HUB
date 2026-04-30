from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ReportJob
from reports.schemas import JobStatus


@dataclass
class ReportJobRecord:
    id: str
    id_chargement: str | None
    original_filename: str
    replace_requested: bool
    status: JobStatus
    progress: int
    raw_object_path: str
    normalized_object_path: str | None = None
    validation_object_path: str | None = None
    dashboard_object_path: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_summary: str | None = None


class ReportJobRepository(Protocol):
    async def create(
        self,
        *,
        job_id: str,
        id_chargement: str | None,
        original_filename: str,
        raw_object_path: str,
        replace_requested: bool,
        created_by: str | None,
    ) -> ReportJobRecord:
        ...

    async def get(self, job_id: str) -> ReportJobRecord | None:
        ...

    async def find_latest_by_business_id(self, id_chargement: str) -> ReportJobRecord | None:
        ...

    async def find_latest_succeeded(self) -> ReportJobRecord | None:
        ...

    async def claim_next_queued(self) -> ReportJobRecord | None:
        ...

    async def mark_running(self, job_id: str) -> None:
        ...

    async def update_progress(self, job_id: str, progress: int) -> None:
        ...

    async def attach_artifacts(
        self,
        job_id: str,
        *,
        normalized_object_path: str | None = None,
        validation_object_path: str | None = None,
        dashboard_object_path: str | None = None,
    ) -> None:
        ...

    async def mark_succeeded(self, job_id: str) -> None:
        ...

    async def mark_failed(self, job_id: str, error_summary: str) -> None:
        ...


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _record_from_model(row: ReportJob) -> ReportJobRecord:
    return ReportJobRecord(
        id=str(row.id),
        id_chargement=row.id_chargement,
        original_filename=row.original_filename,
        replace_requested=row.replace_requested,
        status=row.status,  # type: ignore[arg-type]
        progress=row.progress,
        raw_object_path=row.raw_object_path,
        normalized_object_path=row.normalized_object_path,
        validation_object_path=row.validation_object_path,
        dashboard_object_path=row.dashboard_object_path,
        created_by=str(row.created_by) if row.created_by else None,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        error_summary=row.error_summary,
    )


class SqlAlchemyReportJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        job_id: str,
        id_chargement: str | None,
        original_filename: str,
        raw_object_path: str,
        replace_requested: bool,
        created_by: str | None,
    ) -> ReportJobRecord:
        row = ReportJob(
            id=uuid.UUID(job_id),
            id_chargement=id_chargement,
            original_filename=original_filename,
            replace_requested=replace_requested,
            status="queued",
            progress=0,
            raw_object_path=raw_object_path,
            created_by=uuid.UUID(created_by) if created_by else None,
        )
        self.session.add(row)
        await self.session.flush()
        return _record_from_model(row)

    async def get(self, job_id: str) -> ReportJobRecord | None:
        row = await self.session.get(ReportJob, uuid.UUID(job_id))
        return _record_from_model(row) if row else None

    async def find_latest_by_business_id(self, id_chargement: str) -> ReportJobRecord | None:
        row = await self.session.scalar(
            select(ReportJob)
            .where(ReportJob.id_chargement == id_chargement)
            .order_by(ReportJob.created_at.desc())
            .limit(1)
        )
        return _record_from_model(row) if row else None

    async def find_latest_succeeded(self) -> ReportJobRecord | None:
        row = await self.session.scalar(
            select(ReportJob)
            .where(ReportJob.status == "succeeded")
            .order_by(ReportJob.finished_at.desc().nullslast(), ReportJob.created_at.desc())
            .limit(1)
        )
        return _record_from_model(row) if row else None

    async def claim_next_queued(self) -> ReportJobRecord | None:
        row = await self.session.scalar(
            select(ReportJob)
            .where(ReportJob.status == "queued")
            .order_by(ReportJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return None
        row.status = "running"
        row.progress = max(row.progress, 10)
        row.started_at = _now()
        row.error_summary = None
        await self.session.flush()
        return _record_from_model(row)

    async def mark_running(self, job_id: str) -> None:
        row = await self._require(job_id)
        row.status = "running"
        row.progress = max(row.progress, 10)
        row.started_at = _now()
        row.error_summary = None
        await self.session.flush()

    async def update_progress(self, job_id: str, progress: int) -> None:
        row = await self._require(job_id)
        row.progress = max(0, min(100, progress))
        await self.session.flush()

    async def attach_artifacts(
        self,
        job_id: str,
        *,
        normalized_object_path: str | None = None,
        validation_object_path: str | None = None,
        dashboard_object_path: str | None = None,
    ) -> None:
        row = await self._require(job_id)
        if normalized_object_path is not None:
            row.normalized_object_path = normalized_object_path
        if validation_object_path is not None:
            row.validation_object_path = validation_object_path
        if dashboard_object_path is not None:
            row.dashboard_object_path = dashboard_object_path
        await self.session.flush()

    async def mark_succeeded(self, job_id: str) -> None:
        row = await self._require(job_id)
        row.status = "succeeded"
        row.progress = 100
        row.finished_at = _now()
        row.error_summary = None
        await self.session.flush()

    async def mark_failed(self, job_id: str, error_summary: str) -> None:
        row = await self._require(job_id)
        row.status = "failed"
        row.finished_at = _now()
        row.error_summary = error_summary
        row.progress = max(row.progress, 100 if row.progress >= 90 else row.progress)
        await self.session.flush()

    async def _require(self, job_id: str) -> ReportJob:
        row = await self.session.get(ReportJob, uuid.UUID(job_id))
        if row is None:
            raise KeyError(f"report job {job_id} not found")
        return row


class LocalJsonReportJobRepository:
    """Small development/test repository with the same async contract as the DB adapter."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    async def create(
        self,
        *,
        job_id: str,
        id_chargement: str | None,
        original_filename: str,
        raw_object_path: str,
        replace_requested: bool,
        created_by: str | None,
    ) -> ReportJobRecord:
        record = ReportJobRecord(
            id=job_id,
            id_chargement=id_chargement,
            original_filename=original_filename,
            replace_requested=replace_requested,
            status="queued",
            progress=0,
            raw_object_path=raw_object_path,
            created_by=created_by,
            created_at=_now(),
        )
        self._mutate(lambda data: data.__setitem__(job_id, self._serialize(record)))
        return record

    async def get(self, job_id: str) -> ReportJobRecord | None:
        data = self._read()
        raw = data.get(job_id)
        return self._deserialize(raw) if raw else None

    async def find_latest_by_business_id(self, id_chargement: str) -> ReportJobRecord | None:
        records = [
            self._deserialize(raw)
            for raw in self._read().values()
            if raw.get("id_chargement") == id_chargement
        ]
        records.sort(key=lambda row: row.created_at or datetime.min.replace(tzinfo=UTC))
        return records[-1] if records else None

    async def find_latest_succeeded(self) -> ReportJobRecord | None:
        records = [
            self._deserialize(raw)
            for raw in self._read().values()
            if raw.get("status") == "succeeded"
        ]
        records.sort(
            key=lambda row: (
                row.finished_at or datetime.min.replace(tzinfo=UTC),
                row.created_at or datetime.min.replace(tzinfo=UTC),
            )
        )
        return records[-1] if records else None

    async def claim_next_queued(self) -> ReportJobRecord | None:
        claimed: ReportJobRecord | None = None

        def claim(data: dict[str, dict[str, object]]) -> None:
            nonlocal claimed
            records = [
                self._deserialize(raw)
                for raw in data.values()
                if raw.get("status") == "queued"
            ]
            records.sort(key=lambda row: row.created_at or datetime.min.replace(tzinfo=UTC))
            if not records:
                return
            claimed = records[0]
            claimed.status = "running"
            claimed.progress = max(claimed.progress, 10)
            claimed.started_at = _now()
            claimed.error_summary = None
            data[claimed.id] = self._serialize(claimed)

        self._mutate(claim)
        return claimed

    async def mark_running(self, job_id: str) -> None:
        self._update(job_id, status="running", progress=10, started_at=_now(), error_summary=None)

    async def update_progress(self, job_id: str, progress: int) -> None:
        self._update(job_id, progress=max(0, min(100, progress)))

    async def attach_artifacts(
        self,
        job_id: str,
        *,
        normalized_object_path: str | None = None,
        validation_object_path: str | None = None,
        dashboard_object_path: str | None = None,
    ) -> None:
        values = {
            key: value
            for key, value in {
                "normalized_object_path": normalized_object_path,
                "validation_object_path": validation_object_path,
                "dashboard_object_path": dashboard_object_path,
            }.items()
            if value is not None
        }
        self._update(job_id, **values)

    async def mark_succeeded(self, job_id: str) -> None:
        self._update(job_id, status="succeeded", progress=100, finished_at=_now(), error_summary=None)

    async def mark_failed(self, job_id: str, error_summary: str) -> None:
        self._update(job_id, status="failed", finished_at=_now(), error_summary=error_summary)

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as fh:
            return cast(dict[str, dict[str, object]], json.load(fh))

    def _write(self, data: dict[str, dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def _mutate(self, fn: Callable[[dict[str, dict[str, object]]], None]) -> None:
        with self._lock:
            data = self._read()
            fn(data)
            self._write(data)

    def _update(self, job_id: str, **values: object) -> None:
        def apply(data: dict[str, dict[str, object]]) -> None:
            if job_id not in data:
                raise KeyError(f"report job {job_id} not found")
            data[job_id].update(self._serialize_values(values))

        self._mutate(apply)

    @staticmethod
    def _serialize(record: ReportJobRecord) -> dict[str, object]:
        return LocalJsonReportJobRepository._serialize_values(asdict(record))

    @staticmethod
    def _serialize_values(values: dict[str, object]) -> dict[str, object]:
        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in values.items()
        }

    @staticmethod
    def _deserialize(raw: dict[str, object]) -> ReportJobRecord:
        parsed = dict(raw)
        parsed.setdefault("replace_requested", False)
        for key in ("created_at", "started_at", "finished_at"):
            if isinstance(parsed.get(key), str):
                parsed[key] = datetime.fromisoformat(str(parsed[key]))
        return ReportJobRecord(**parsed)  # type: ignore[arg-type]
