from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class BuildRequest(BaseModel):
    source_key: str = "rsu-csv"
    compatibility_profile: Literal["julia-30d-v1"] = "julia-30d-v1"
    include_score_variables: bool = True


class SourceFileResponse(BaseModel):
    logical_name: str
    relative_path: str
    sha256: str
    byte_size: int
    row_count: int | None
    required: bool


class QualityCheckResponse(BaseModel):
    check_key: str
    severity: str
    passed: bool
    observed_value: str | None
    expected_value: str | None
    details: dict[str, Any] = Field(default_factory=dict)


class BatchResponse(BaseModel):
    id: str
    source_key: str
    pipeline_version: str
    content_hash: str | None
    status: str
    stage: str
    progress: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_summary: str | None


class BatchDetailResponse(BatchResponse):
    files: list[SourceFileResponse] = Field(default_factory=list)
    quality_checks: list[QualityCheckResponse] = Field(default_factory=list)
    core_version: str | None = None
    release_key: str | None = None


class ReleaseResponse(BaseModel):
    release_key: str
    core_version: str
    products: dict[str, Any]
    is_active: bool
    published_at: datetime
    period_start: date | None
    period_end: date | None


class AnalyticsFilters(BaseModel):
    subject: Literal["ALL", "ASD", "AMOT"] = "ALL"
    region_id: int | None = None
    province_id: int | None = None
    start_date: date
    end_date: date
    granularity: Literal["day", "week", "month", "quarter"] = "month"

    @model_validator(mode="after")
    def validate_period_and_geography(self) -> AnalyticsFilters:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if (self.end_date - self.start_date).days > 3660:
            raise ValueError("selected period cannot exceed 10 years")
        return self


class GeographyOption(BaseModel):
    id: int
    label: str
    parent_id: int | None = None


class FilterOptionsResponse(BaseModel):
    release_key: str
    period_start: date
    period_end: date
    subjects: list[dict[str, str]]
    regions: list[GeographyOption]
    provinces: list[GeographyOption]

