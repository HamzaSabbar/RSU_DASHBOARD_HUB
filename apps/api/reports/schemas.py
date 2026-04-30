from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal["queued", "running", "succeeded", "failed"]
ValidationSeverity = Literal["error", "warning", "info"]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ValidationMessage(ApiModel):
    severity: ValidationSeverity
    sheet: str | None = None
    section: str | None = None
    row: int | None = None
    column: str | None = None
    code: str
    message: str


class ValidationSummary(ApiModel):
    errors: int = 0
    warnings: int = 0
    infos: int = 0


class ValidationResult(ApiModel):
    job_id: str | None = Field(default=None, alias="jobId")
    id_chargement: str | None = Field(default=None, alias="idChargement")
    summary: ValidationSummary = Field(default_factory=ValidationSummary)
    messages: list[ValidationMessage] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return self.summary.errors > 0


class ReportJobCreateResponse(ApiModel):
    job_id: str = Field(alias="jobId")
    status: JobStatus
    status_url: str = Field(alias="statusUrl")
    dashboard_url: str = Field(alias="dashboardUrl")
    validation_url: str = Field(alias="validationUrl")


class ReportJobStatusResponse(ApiModel):
    job_id: str = Field(alias="jobId")
    status: JobStatus
    progress: int
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime | None = Field(default=None, alias="startedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")
    error_summary: str | None = Field(default=None, alias="errorSummary")


class DashboardUnavailable(ApiModel):
    job_id: str = Field(alias="jobId")
    status: JobStatus
    message: str
    validation_url: str = Field(alias="validationUrl")


DashboardJson = dict[str, Any]
