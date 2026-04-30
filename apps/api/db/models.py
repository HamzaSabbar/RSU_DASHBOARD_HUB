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
            "ix_report_upload_batches_active_id_chargement",
            "id_chargement",
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
