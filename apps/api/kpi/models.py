"""SQLAlchemy models for the 18 RSU process KPIs plus import provenance.

Every KPI has its own typed fact table (never a shared EAV blob) with only the
dimension/measure columns that KPI's source sheet actually carries. Three side
tables (`kpi_ins_02_national`, `kpi_maj_01_national`, `kpi_ins_03_field`) hold
the workbook's dedicated national-summary / field-analysis blocks.

Every main table shares one dimension column name for its primary time
dimension: `period`. Its true semantics (month, quarter, cutoff/month-end
date) vary by KPI per `docs/DATA_CONTRACT.md`, but a single stable column
name lets the analytics layer compute month-over-month deltas generically
without per-KPI special-casing.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class KpiImport(Base):
    """One committed (or attempted) workbook import — the provenance anchor."""

    __tablename__ = "kpi_imports"

    id: Mapped[uuid.UUID] = _uuid_pk()
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    recognized_sheets: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    missing_sheets: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    unknown_sheets: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    row_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    period_min: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_max: Mapped[date | None] = mapped_column(Date, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KpiGeography(Base):
    """Derived region/province/milieu vocabulary seen across imports.

    Not a source of truth and not an FK target — purely a cheap index so
    `GET /api/kpi/filters` doesn't have to UNION across up to 25 fact tables.
    Upserted as a side effect of every commit.
    """

    __tablename__ = "kpi_geography"

    id: Mapped[uuid.UUID] = _uuid_pk()
    region: Mapped[str] = mapped_column(String(128), nullable=False)
    province: Mapped[str | None] = mapped_column(String(128), nullable=True)
    milieu: Mapped[str | None] = mapped_column(String(16), nullable=True)

    __table_args__ = (
        UniqueConstraint("region", "province", "milieu", name="kpi_geography_triple_uq"),
    )


class _ProvenanceMixin:
    """Common provenance/audit columns shared by every KPI fact table."""

    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @declared_attr
    def first_seen_import_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False)

    @declared_attr
    def last_import_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False)


# ---------------------------------------------------------------------------
# Accès
# ---------------------------------------------------------------------------


class KpiAcc01(_ProvenanceMixin, Base):
    __tablename__ = "kpi_acc_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    age_band: Mapped[str] = mapped_column(String(32), nullable=False)
    present_rsu_30j: Mapped[int] = mapped_column(Integer, nullable=False)
    present_rsu_90j: Mapped[int] = mapped_column(Integer, nullable=False)
    rnp_idcs_actif: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period", "region", "province", "milieu", "age_band", name="kpi_acc_01_nk"
        ),
    )


# ---------------------------------------------------------------------------
# Inscription
# ---------------------------------------------------------------------------


class KpiIns01(_ProvenanceMixin, Base):
    __tablename__ = "kpi_ins_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    finalisees_30j: Mapped[int] = mapped_column(Integer, nullable=False)
    finalisees_60j: Mapped[int] = mapped_column(Integer, nullable=False)
    finalisees_90j: Mapped[int] = mapped_column(Integer, nullable=False)
    demandes_initiees: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period", "region", "province", "milieu", "channel", name="kpi_ins_01_nk"
        ),
    )


class KpiIns02(_ProvenanceMixin, Base):
    __tablename__ = "kpi_ins_02"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    dossiers_finalises: Mapped[int] = mapped_column(Integer, nullable=False)
    mediane_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p75_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p90_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period", "region", "province", "milieu", "channel", name="kpi_ins_02_nk"
        ),
    )


class KpiIns02National(_ProvenanceMixin, Base):
    """INS-02 national summary (workbook cols K:N) — the only valid source of
    a national median/P75/P90 for this KPI. Never derived from `kpi_ins_02`."""

    __tablename__ = "kpi_ins_02_national"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    mediane_nationale: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p75_national: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p90_national: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)


class KpiIns03(_ProvenanceMixin, Base):
    """INS-03 global table (workbook cols A:F)."""

    __tablename__ = "kpi_ins_03"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    personnes_avec_incoherence: Mapped[int] = mapped_column(Integer, nullable=False)
    personnes_comparees: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("period", "region", "province", "milieu", name="kpi_ins_03_nk"),
    )


class KpiIns03Field(_ProvenanceMixin, Base):
    """INS-03 field-analysis table (workbook cols H:O)."""

    __tablename__ = "kpi_ins_03_field"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    controlled_field: Mapped[str] = mapped_column(String(128), nullable=False)
    incoherence_type: Mapped[str] = mapped_column(String(128), nullable=False)
    nb_incoherents: Mapped[int] = mapped_column(Integer, nullable=False)
    personnes_comparees: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period",
            "region",
            "province",
            "milieu",
            "controlled_field",
            "incoherence_type",
            name="kpi_ins_03_field_nk",
        ),
    )


# ---------------------------------------------------------------------------
# Fiabilisation des sources
# ---------------------------------------------------------------------------


class KpiFsc01(_ProvenanceMixin, Base):
    __tablename__ = "kpi_fsc_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    administrative_source: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    flow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    requetes_valides: Mapped[int] = mapped_column(Integer, nullable=False)
    delai_moyen_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    delai_median_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p90_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period", "administrative_source", "flow_type", name="kpi_fsc_01_nk"
        ),
    )


# ---------------------------------------------------------------------------
# Mise à jour & rescoring
# ---------------------------------------------------------------------------


class KpiMaj01(_ProvenanceMixin, Base):
    __tablename__ = "kpi_maj_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    update_type: Mapped[str] = mapped_column(String(64), nullable=False)
    complexity: Mapped[str] = mapped_column(String(32), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    maj_finalisees: Mapped[int] = mapped_column(Integer, nullable=False)
    dossiers_concernes: Mapped[int] = mapped_column(Integer, nullable=False)
    mediane_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p75_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p90_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period",
            "update_type",
            "complexity",
            "region",
            "province",
            "milieu",
            "channel",
            name="kpi_maj_01_nk",
        ),
    )


class KpiMaj01National(_ProvenanceMixin, Base):
    """MAJ-01 national summary (workbook cols N:Q)."""

    __tablename__ = "kpi_maj_01_national"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    mediane_delai_national: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p75_national: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p90_national: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)


class KpiMaj02(_ProvenanceMixin, Base):
    """`period` here is the arrêté / month-end stock date."""

    __tablename__ = "kpi_maj_02"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    update_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    maj_en_cours: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period",
            "update_type",
            "channel",
            "region",
            "province",
            "milieu",
            name="kpi_maj_02_nk",
        ),
    )


class KpiMaj03(_ProvenanceMixin, Base):
    __tablename__ = "kpi_maj_03"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    update_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    demandes_maj_initiees: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period",
            "update_type",
            "channel",
            "region",
            "province",
            "milieu",
            name="kpi_maj_03_nk",
        ),
    )


class KpiMaj04(_ProvenanceMixin, Base):
    """`period` here is the cutoff (`date d'arrêté`) date."""

    __tablename__ = "kpi_maj_04"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    menages_non_rescores_365j: Mapped[int] = mapped_column(Integer, nullable=False)
    menages_actifs: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("period", "region", "province", "milieu", name="kpi_maj_04_nk"),
    )


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------


class KpiNot01(_ProvenanceMixin, Base):
    """Formerly NOT-02 (OTP-only ratio); renumbered and its formula widened
    to a union of OTP + notification activity -- `chefs_avec_activite_observee`
    is the precomputed union column and the only valid ratio numerator
    (never `chefs_avec_otp_reussi + chefs_avec_notification_recue`, since a
    chef can trigger both and that would double-count the overlap)."""

    __tablename__ = "kpi_not_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    age_band: Mapped[str] = mapped_column(String(32), nullable=False)
    chefs_avec_otp_reussi: Mapped[int] = mapped_column(Integer, nullable=False)
    chefs_avec_numero_enregistre: Mapped[int] = mapped_column(Integer, nullable=False)
    chefs_avec_notification_recue: Mapped[int] = mapped_column(Integer, nullable=False)
    chefs_avec_activite_observee: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period",
            "region",
            "province",
            "milieu",
            "gender",
            "age_band",
            name="kpi_not_01_nk",
        ),
    )


class KpiNot02(_ProvenanceMixin, Base):
    """Formerly NOT-03 (courrier postal); renumbered only, formula unchanged."""

    __tablename__ = "kpi_not_02"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mail_type: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    courriers_livres: Mapped[int] = mapped_column(Integer, nullable=False)
    courriers_envoyes_observables: Mapped[int] = mapped_column(Integer, nullable=False)
    non_livres_retournes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    en_acheminement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motif_principal_non_livraison: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period", "mail_type", "region", "province", "milieu", name="kpi_not_02_nk"
        ),
    )


# ---------------------------------------------------------------------------
# Recours & réclamations
# ---------------------------------------------------------------------------


class KpiRec01(_ProvenanceMixin, Base):
    """`period` here is the deposit month."""

    __tablename__ = "kpi_rec_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recourse_motive: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    nb_decisions_finales: Mapped[int] = mapped_column(Integer, nullable=False)
    delai_moyen_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period", "recourse_motive", "region", "province", "milieu", name="kpi_rec_01_nk"
        ),
    )


class KpiRec02(_ProvenanceMixin, Base):
    __tablename__ = "kpi_rec_02"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recourse_motive: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    recours_en_cours: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period", "recourse_motive", "region", "province", name="kpi_rec_02_nk"
        ),
    )


class KpiRec03(_ProvenanceMixin, Base):
    """Formerly REC-04; renumbered, and later gained région/province/milieu.
    `period` here is the decision month."""

    __tablename__ = "kpi_rec_03"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recourse_motive: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    recours_acceptes: Mapped[int] = mapped_column(Integer, nullable=False)
    recours_decision_finale: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period", "recourse_motive", "region", "province", "milieu", name="kpi_rec_03_nk"
        ),
    )


class KpiRec04(_ProvenanceMixin, Base):
    """Formerly REC-06; renumbered only. `period` here is the deposit month;
    `channel` is Portail / CSC.

    `nb_reclamations_cloturees` ("clôturés") is a flow, safe to sum across
    periods; `reclamations_en_cours` ("en cours") is a stock/snapshot and
    must only ever be read for the most recent period in a group -- see
    `KpiSpec.extra_measures` / `analytics.aggregate_latest`. Absorbs the
    concept formerly tracked by the now-retired `KpiRec07`.
    """

    __tablename__ = "kpi_rec_04"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    nb_reclamations_cloturees: Mapped[int] = mapped_column(Integer, nullable=False)
    delai_moyen_jours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    reclamations_en_cours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period", "channel", "region", "province", "milieu", name="kpi_rec_04_nk"
        ),
    )


class KpiRec05(_ProvenanceMixin, Base):
    """Formerly REC-08; renumbered only."""

    __tablename__ = "kpi_rec_05"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    reclamations: Mapped[int] = mapped_column(Integer, nullable=False)
    preinscriptions: Mapped[int] = mapped_column(Integer, nullable=False)
    demandes_maj: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "period", "region", "province", "milieu", name="kpi_rec_05_nk"
        ),
    )


# ---------------------------------------------------------------------------
# Contrôle qualité
# ---------------------------------------------------------------------------


class KpiCqd01(_ProvenanceMixin, Base):
    __tablename__ = "kpi_cqd_01"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    suspicion_rule: Mapped[str] = mapped_column(String(128), nullable=False)
    suspected_fraud_type: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    fraudes_averees: Mapped[int] = mapped_column(Integer, nullable=False)
    suspicions_cloturees_evaluables: Mapped[int] = mapped_column(Integer, nullable=False)
    suspicions_en_traitement: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period",
            "suspicion_rule",
            "suspected_fraud_type",
            "region",
            "province",
            "milieu",
            name="kpi_cqd_01_nk",
        ),
    )


class KpiCqd02(_ProvenanceMixin, Base):
    __tablename__ = "kpi_cqd_02"

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    milieu: Mapped[str] = mapped_column(String(16), nullable=False)
    menages_actifs: Mapped[int] = mapped_column(Integer, nullable=False)
    menages_soupconnes_rouge: Mapped[int] = mapped_column(Integer, nullable=False)
    menages_soupconnes_orange: Mapped[int] = mapped_column(Integer, nullable=False)
    # Often blank in the real workbook -- the KPI's "total" is derived as
    # rouge + orange (see kpi/specs.py CQD-02 ratio_windows), never read back
    # from this column for the ratio itself; stored only for an optional
    # cross-check (SumEquals) when the source does fill it in.
    menages_distincts_soupconnes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period", "region", "province", "milieu", name="kpi_cqd_02_nk"
        ),
    )
