from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="admin")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'viewer', 'editor')", name="users_role_check"),
    )


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    uploads: Mapped[list[Upload]] = relationship(back_populates="board")
    snapshots: Mapped[list[BoardSnapshot]] = relationship(back_populates="board")


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = _uuid_pk()
    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    file_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    board: Mapped[Board] = relationship(back_populates="uploads")

    __table_args__ = (
        CheckConstraint("status IN ('accepted', 'rejected')", name="uploads_status_check"),
    )


class BoardSnapshot(Base):
    __tablename__ = "board_snapshots"

    id: Mapped[uuid.UUID] = _uuid_pk()
    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reporting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    computed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    board: Mapped[Board] = relationship(back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint("board_id", "reporting_date", name="board_snapshots_board_date_uq"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    audit_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReportJob(Base):
    __tablename__ = "report_jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    id_chargement: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    replace_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_object_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_object_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    validation_object_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dashboard_object_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="report_jobs_status_check",
        ),
    )


class DataSourceBatch(Base):
    """One immutable client CSV delivery and its asynchronous build state."""

    __tablename__ = "data_source_batches"

    id: Mapped[uuid.UUID] = _uuid_pk()
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, default="rsu-csv")
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pipeline_version: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="data_source_batches_status_check",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="data_source_batches_progress_check",
        ),
    )


class DataSourceFile(Base):
    __tablename__ = "data_source_files"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_source_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    logical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Numeric(20, 0), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("batch_id", "logical_name", name="data_source_files_batch_name_uq"),
    )


class CoreDatasetVersion(Base):
    __tablename__ = "core_dataset_versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_source_batches.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    version_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="building", index=True)
    dataset_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    database_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    manifest_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    row_counts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('building', 'ready', 'failed')",
            name="core_dataset_versions_status_check",
        ),
    )


class DataProductBuild(Base):
    __tablename__ = "data_product_builds"

    id: Mapped[uuid.UUID] = _uuid_pk()
    core_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core_dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    product_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="building", index=True)
    artifact_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    row_counts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('building', 'ready', 'failed')",
            name="data_product_builds_status_check",
        ),
        UniqueConstraint(
            "core_version_id", "product_slug", "product_version",
            name="data_product_builds_version_uq",
        ),
    )


class DatasetArtifact(Base):
    __tablename__ = "dataset_artifacts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    core_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core_dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_build_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_product_builds.id", ondelete="CASCADE"), nullable=True, index=True
    )
    layer: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_name: Mapped[str] = mapped_column(String(160), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Numeric(20, 0), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "core_version_id", "artifact_name", name="dataset_artifacts_core_name_uq"
        ),
    )


class DatasetQualityCheck(Base):
    __tablename__ = "dataset_quality_checks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_source_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    core_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core_dataset_versions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    check_key: Mapped[str] = mapped_column(String(160), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    observed_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="dataset_quality_checks_severity_check",
        ),
        UniqueConstraint("batch_id", "check_key", name="dataset_quality_checks_batch_key_uq"),
    )


class PlatformRelease(Base):
    __tablename__ = "platform_releases"

    id: Mapped[uuid.UUID] = _uuid_pk()
    release_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    core_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core_dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    products_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_platform_releases_single_active",
            "is_active",
            unique=True,
            postgresql_where=is_active.is_(True),
        ),
    )


class ReportUploadBatch(Base):
    __tablename__ = "report_upload_batches"

    id: Mapped[uuid.UUID] = _uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    id_chargement: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    systeme_source: Mapped[str] = mapped_column(String(255), nullable=False, default="system", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_object_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_object_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    validation_object_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    dashboard_object_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="report_upload_batches_status_check",
        ),
        Index(
            "ix_report_upload_batches_active_source_period",
            "systeme_source",
            "period_start",
            "period_end",
            unique=True,
            postgresql_where=is_active.is_(True),
        ),
    )


class ReportRegionFact(Base):
    __tablename__ = "report_regions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nom_region: Mapped[str] = mapped_column(String(255), nullable=False)
    ordre_affichage: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReportProvinceFact(Base):
    __tablename__ = "report_provinces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nom_province: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ordre_affichage: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReportCodeFact(Base):
    __tablename__ = "report_codes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    libelle: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ordre_affichage: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReportRsuStockFact(Base):
    __tablename__ = "report_rsu_stock"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_reference: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code_registre: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    type_unite: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_cumule: Mapped[int] = mapped_column(Integer, nullable=False)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportRsuFlowFact(Base):
    __tablename__ = "report_rsu_flow"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    debut_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_evenement: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mois_evenement: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    code_region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nom_province: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    code_registre: Mapped[str] = mapped_column(String(64), nullable=False, default="RNP", index=True)
    type_unite: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nb_nouvelles_inscriptions: Mapped[int] = mapped_column(Integer, nullable=False)
    mode_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportRsuAnnotationFact(Base):
    __tablename__ = "report_rsu_annotations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_graphique: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mois_evenement: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    libelle_annotation: Mapped[str | None] = mapped_column(Text, nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportProgramStockFact(Base):
    __tablename__ = "report_program_stock"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_programme: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    date_reference: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    type_unite: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nb_actifs: Mapped[int] = mapped_column(Integer, nullable=False)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportProgramFlowFact(Base):
    __tablename__ = "report_program_flow"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_programme: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    debut_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_evenement: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mois_evenement: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    code_region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nom_province: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    nb_entrants_menages: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_sortants_menages: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_entrants_personnes: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_sortants_personnes: Mapped[int] = mapped_column(Integer, nullable=False)
    montant_mensuel_entrants_dh: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    montant_mensuel_sortants_dh: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportProgramRescoringFact(Base):
    __tablename__ = "report_program_rescoring"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_programme: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    debut_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_evenement: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mois_evenement: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    code_region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nom_province: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    nb_sortants_menages: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_sortants_personnes: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_menages_non_communiques: Mapped[int] = mapped_column(Integer, nullable=False)
    montant_mensuel_arrete_dh: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportProgramFraudFact(Base):
    __tablename__ = "report_program_fraud"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_programme: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    debut_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_periode: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_evenement: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mois_evenement: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    code_region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nom_province: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    radiated_hh_count: Mapped[int] = mapped_column(Integer, nullable=False)
    radiated_persons: Mapped[int] = mapped_column(Integer, nullable=False)
    montant_mensuel_arrete_dh: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportFmsTreatmentFact(Base):
    __tablename__ = "report_fms_treatment"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_reference: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    debut_periode: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fin_periode: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    date_evenement: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    mois_evenement: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    code_type_famille: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_niveau_risque: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_perimetre_programme: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    code_region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nom_province: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    demandes_injectees: Mapped[int] = mapped_column(Integer, nullable=False)
    demandes_traitees: Mapped[int] = mapped_column(Integer, nullable=False)
    doute_confirme: Mapped[int] = mapped_column(Integer, nullable=False)
    doute_leve: Mapped[int] = mapped_column(Integer, nullable=False)
    en_attente: Mapped[int] = mapped_column(Integer, nullable=False)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportFmsBlockedFact(Base):
    __tablename__ = "report_fms_blocked"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_reference: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    debut_periode: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fin_periode: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    date_evenement: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    mois_evenement: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    code_motif_blocage: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_type_famille: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    code_region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nom_province: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    nb_menages_bloques: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_personnes_bloquees: Mapped[int] = mapped_column(Integer, nullable=False)
    systeme_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportAmountRuleFact(Base):
    __tablename__ = "report_amount_rules"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_programme: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    date_effet_debut: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_effet_fin: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    code_type_famille: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    unite_beneficiaire: Mapped[str | None] = mapped_column(String(128), nullable=True)
    type_montant: Mapped[str | None] = mapped_column(String(128), nullable=True)
    montant_mensuel_dh: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    facteur_annualisation: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)
