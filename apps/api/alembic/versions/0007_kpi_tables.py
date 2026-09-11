"""22 RSU process KPI fact tables + import provenance

Adds the typed storage for the new single KPI dashboard: one fact table per
KPI code (never a shared EAV blob, per docs/DATA_CONTRACT.md), three side
tables for the workbook's dedicated national-percentile / field-analysis
blocks (kpi_ins_02_national, kpi_maj_01_national, kpi_ins_03_field), an
import/provenance table (kpi_imports), and a derived geography index
(kpi_geography). Added additively -- legacy tables are untouched here and
dropped in a later migration once the new KPI path is verified end-to-end.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-07

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kpi_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("recognized_sheets", postgresql.JSONB(), nullable=False),
        sa.Column("missing_sheets", postgresql.JSONB(), nullable=False),
        sa.Column("unknown_sheets", postgresql.JSONB(), nullable=False),
        sa.Column("row_counts", postgresql.JSONB(), nullable=False),
        sa.Column("period_min", sa.Date(), nullable=True),
        sa.Column("period_max", sa.Date(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_kpi_imports_checksum", "kpi_imports", ["checksum"], unique=True)
    op.create_index("ix_kpi_imports_status", "kpi_imports", ["status"])
    op.create_index("ix_kpi_imports_uploaded_at", "kpi_imports", ["uploaded_at"])

    op.create_table(
        "kpi_geography",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=True),
        sa.Column("milieu", sa.String(16), nullable=True),
        sa.UniqueConstraint("region", "province", "milieu", name="kpi_geography_triple_uq"),
    )

    op.create_table(
        "kpi_acc_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("age_band", sa.String(32), nullable=False),
        sa.Column("present_rsu_30j", sa.Integer(), nullable=False),
        sa.Column("present_rsu_90j", sa.Integer(), nullable=False),
        sa.Column("rnp_idcs_actif", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "age_band", name="kpi_acc_01_nk"),
    )
    op.create_index("ix_kpi_acc_01_province", "kpi_acc_01", ["province"])
    op.create_index("ix_kpi_acc_01_period", "kpi_acc_01", ["period"])
    op.create_index("ix_kpi_acc_01_region", "kpi_acc_01", ["region"])

    op.create_table(
        "kpi_ins_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("finalisees_30j", sa.Integer(), nullable=False),
        sa.Column("finalisees_60j", sa.Integer(), nullable=False),
        sa.Column("finalisees_90j", sa.Integer(), nullable=False),
        sa.Column("demandes_initiees", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "channel", name="kpi_ins_01_nk"),
    )
    op.create_index("ix_kpi_ins_01_province", "kpi_ins_01", ["province"])
    op.create_index("ix_kpi_ins_01_region", "kpi_ins_01", ["region"])
    op.create_index("ix_kpi_ins_01_period", "kpi_ins_01", ["period"])

    op.create_table(
        "kpi_ins_02",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("dossiers_finalises", sa.Integer(), nullable=False),
        sa.Column("mediane_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("p75_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("p90_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "channel", name="kpi_ins_02_nk"),
    )
    op.create_index("ix_kpi_ins_02_period", "kpi_ins_02", ["period"])
    op.create_index("ix_kpi_ins_02_province", "kpi_ins_02", ["province"])
    op.create_index("ix_kpi_ins_02_region", "kpi_ins_02", ["region"])

    op.create_table(
        "kpi_ins_02_national",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False, unique=True),
        sa.Column("mediane_nationale", sa.Numeric(10, 2), nullable=True),
        sa.Column("p75_national", sa.Numeric(10, 2), nullable=True),
        sa.Column("p90_national", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_kpi_ins_02_national_period", "kpi_ins_02_national", ["period"], unique=True)

    op.create_table(
        "kpi_ins_03",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("personnes_avec_incoherence", sa.Integer(), nullable=False),
        sa.Column("personnes_comparees", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", name="kpi_ins_03_nk"),
    )
    op.create_index("ix_kpi_ins_03_period", "kpi_ins_03", ["period"])
    op.create_index("ix_kpi_ins_03_region", "kpi_ins_03", ["region"])
    op.create_index("ix_kpi_ins_03_province", "kpi_ins_03", ["province"])

    op.create_table(
        "kpi_ins_03_field",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("controlled_field", sa.String(128), nullable=False),
        sa.Column("incoherence_type", sa.String(128), nullable=False),
        sa.Column("nb_incoherents", sa.Integer(), nullable=False),
        sa.Column("personnes_comparees", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "controlled_field", "incoherence_type", name="kpi_ins_03_field_nk"),
    )
    op.create_index("ix_kpi_ins_03_field_period", "kpi_ins_03_field", ["period"])
    op.create_index("ix_kpi_ins_03_field_region", "kpi_ins_03_field", ["region"])
    op.create_index("ix_kpi_ins_03_field_province", "kpi_ins_03_field", ["province"])

    op.create_table(
        "kpi_fsc_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("administrative_source", sa.String(128), nullable=False),
        sa.Column("flow_type", sa.String(64), nullable=False),
        sa.Column("requetes_valides", sa.Integer(), nullable=False),
        sa.Column("delai_moyen_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("delai_median_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("p90_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "administrative_source", "flow_type", name="kpi_fsc_01_nk"),
    )
    op.create_index("ix_kpi_fsc_01_administrative_source", "kpi_fsc_01", ["administrative_source"])
    op.create_index("ix_kpi_fsc_01_period", "kpi_fsc_01", ["period"])

    op.create_table(
        "kpi_maj_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("update_type", sa.String(64), nullable=False),
        sa.Column("complexity", sa.String(32), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("maj_finalisees", sa.Integer(), nullable=False),
        sa.Column("dossiers_concernes", sa.Integer(), nullable=False),
        sa.Column("mediane_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("p75_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("p90_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "update_type", "complexity", "region", "province", "milieu", "channel", name="kpi_maj_01_nk"),
    )
    op.create_index("ix_kpi_maj_01_period", "kpi_maj_01", ["period"])
    op.create_index("ix_kpi_maj_01_province", "kpi_maj_01", ["province"])
    op.create_index("ix_kpi_maj_01_region", "kpi_maj_01", ["region"])

    op.create_table(
        "kpi_maj_01_national",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False, unique=True),
        sa.Column("mediane_delai_national", sa.Numeric(10, 2), nullable=True),
        sa.Column("p75_national", sa.Numeric(10, 2), nullable=True),
        sa.Column("p90_national", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_kpi_maj_01_national_period", "kpi_maj_01_national", ["period"], unique=True)

    op.create_table(
        "kpi_maj_02",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("update_type", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("maj_en_cours", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "update_type", "channel", "region", "province", "milieu", name="kpi_maj_02_nk"),
    )
    op.create_index("ix_kpi_maj_02_period", "kpi_maj_02", ["period"])
    op.create_index("ix_kpi_maj_02_province", "kpi_maj_02", ["province"])
    op.create_index("ix_kpi_maj_02_region", "kpi_maj_02", ["region"])

    op.create_table(
        "kpi_maj_03",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("update_type", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("demandes_maj_initiees", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "update_type", "channel", "region", "province", "milieu", name="kpi_maj_03_nk"),
    )
    op.create_index("ix_kpi_maj_03_period", "kpi_maj_03", ["period"])
    op.create_index("ix_kpi_maj_03_region", "kpi_maj_03", ["region"])
    op.create_index("ix_kpi_maj_03_province", "kpi_maj_03", ["province"])

    op.create_table(
        "kpi_maj_04",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("menages_non_rescores_365j", sa.Integer(), nullable=False),
        sa.Column("menages_actifs", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", name="kpi_maj_04_nk"),
    )
    op.create_index("ix_kpi_maj_04_region", "kpi_maj_04", ["region"])
    op.create_index("ix_kpi_maj_04_period", "kpi_maj_04", ["period"])
    op.create_index("ix_kpi_maj_04_province", "kpi_maj_04", ["province"])

    op.create_table(
        "kpi_not_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("gender", sa.String(16), nullable=False),
        sa.Column("numeros_non_operationnels", sa.Integer(), nullable=False),
        sa.Column("numeros_controles", sa.Integer(), nullable=False),
        sa.Column("injoignables", sa.Integer(), nullable=True),
        sa.Column("titulaire_different", sa.Integer(), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "gender", name="kpi_not_01_nk"),
    )
    op.create_index("ix_kpi_not_01_region", "kpi_not_01", ["region"])
    op.create_index("ix_kpi_not_01_province", "kpi_not_01", ["province"])
    op.create_index("ix_kpi_not_01_period", "kpi_not_01", ["period"])

    op.create_table(
        "kpi_not_02",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("gender", sa.String(16), nullable=False),
        sa.Column("age_band", sa.String(32), nullable=False),
        sa.Column("chefs_avec_otp_reussi", sa.Integer(), nullable=False),
        sa.Column("chefs_avec_numero_enregistre", sa.Integer(), nullable=False),
        sa.Column("total_otp_reussis", sa.Integer(), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "gender", "age_band", name="kpi_not_02_nk"),
    )
    op.create_index("ix_kpi_not_02_region", "kpi_not_02", ["region"])
    op.create_index("ix_kpi_not_02_province", "kpi_not_02", ["province"])
    op.create_index("ix_kpi_not_02_period", "kpi_not_02", ["period"])

    op.create_table(
        "kpi_not_03",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("mail_type", sa.String(64), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("courriers_livres", sa.Integer(), nullable=False),
        sa.Column("courriers_envoyes_observables", sa.Integer(), nullable=False),
        sa.Column("non_livres_retournes", sa.Integer(), nullable=True),
        sa.Column("en_acheminement", sa.Integer(), nullable=True),
        sa.Column("motif_principal_non_livraison", sa.String(255), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "mail_type", "region", "province", "milieu", name="kpi_not_03_nk"),
    )
    op.create_index("ix_kpi_not_03_period", "kpi_not_03", ["period"])
    op.create_index("ix_kpi_not_03_province", "kpi_not_03", ["province"])
    op.create_index("ix_kpi_not_03_region", "kpi_not_03", ["region"])

    op.create_table(
        "kpi_rec_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("recourse_motive", sa.String(128), nullable=False),
        sa.Column("nb_decisions_finales", sa.Integer(), nullable=False),
        sa.Column("delai_moyen_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "recourse_motive", name="kpi_rec_01_nk"),
    )
    op.create_index("ix_kpi_rec_01_period", "kpi_rec_01", ["period"])

    op.create_table(
        "kpi_rec_02",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("recourse_motive", sa.String(128), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("recours_en_cours", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "recourse_motive", "region", "province", name="kpi_rec_02_nk"),
    )
    op.create_index("ix_kpi_rec_02_region", "kpi_rec_02", ["region"])
    op.create_index("ix_kpi_rec_02_province", "kpi_rec_02", ["province"])
    op.create_index("ix_kpi_rec_02_period", "kpi_rec_02", ["period"])

    op.create_table(
        "kpi_rec_03",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False, unique=True),
        sa.Column("menages_avec_recours_60j", sa.Integer(), nullable=False),
        sa.Column("menages_eligibles_fenetre_60j", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_kpi_rec_03_period", "kpi_rec_03", ["period"], unique=True)

    op.create_table(
        "kpi_rec_04",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("recourse_motive", sa.String(128), nullable=False),
        sa.Column("recours_acceptes", sa.Integer(), nullable=False),
        sa.Column("recours_decision_finale", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "recourse_motive", name="kpi_rec_04_nk"),
    )
    op.create_index("ix_kpi_rec_04_period", "kpi_rec_04", ["period"])

    op.create_table(
        "kpi_rec_05",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("recourse_motive", sa.String(128), nullable=False),
        sa.Column("recours_deposes", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "recourse_motive", name="kpi_rec_05_nk"),
    )
    op.create_index("ix_kpi_rec_05_period", "kpi_rec_05", ["period"])

    op.create_table(
        "kpi_rec_06",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("nb_reclamations_cloturees", sa.Integer(), nullable=False),
        sa.Column("delai_moyen_jours", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "channel", name="kpi_rec_06_nk"),
    )
    op.create_index("ix_kpi_rec_06_period", "kpi_rec_06", ["period"])

    op.create_table(
        "kpi_rec_07",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("complaint_motive", sa.String(128), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("reclamations_en_cours", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "channel", "complaint_motive", "region", "province", name="kpi_rec_07_nk"),
    )
    op.create_index("ix_kpi_rec_07_period", "kpi_rec_07", ["period"])
    op.create_index("ix_kpi_rec_07_province", "kpi_rec_07", ["province"])
    op.create_index("ix_kpi_rec_07_region", "kpi_rec_07", ["region"])

    op.create_table(
        "kpi_rec_08",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False, unique=True),
        sa.Column("reclamations", sa.Integer(), nullable=False),
        sa.Column("preinscriptions", sa.Integer(), nullable=False),
        sa.Column("demandes_maj", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_kpi_rec_08_period", "kpi_rec_08", ["period"], unique=True)

    op.create_table(
        "kpi_cqd_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("suspicion_rule", sa.String(128), nullable=False),
        sa.Column("suspected_fraud_type", sa.String(128), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("fraudes_averees", sa.Integer(), nullable=False),
        sa.Column("suspicions_cloturees_evaluables", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "suspicion_rule", "suspected_fraud_type", "region", "province", "milieu", name="kpi_cqd_01_nk"),
    )
    op.create_index("ix_kpi_cqd_01_period", "kpi_cqd_01", ["period"])
    op.create_index("ix_kpi_cqd_01_region", "kpi_cqd_01", ["region"])
    op.create_index("ix_kpi_cqd_01_province", "kpi_cqd_01", ["province"])

    op.create_table(
        "kpi_cqd_02",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("menages_distincts_soupconnes", sa.Integer(), nullable=False),
        sa.Column("menages_actifs", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", name="kpi_cqd_02_nk"),
    )
    op.create_index("ix_kpi_cqd_02_period", "kpi_cqd_02", ["period"])
    op.create_index("ix_kpi_cqd_02_province", "kpi_cqd_02", ["province"])
    op.create_index("ix_kpi_cqd_02_region", "kpi_cqd_02", ["region"])


def downgrade() -> None:
    op.drop_table("kpi_cqd_02")
    op.drop_table("kpi_cqd_01")
    op.drop_table("kpi_rec_08")
    op.drop_table("kpi_rec_07")
    op.drop_table("kpi_rec_06")
    op.drop_table("kpi_rec_05")
    op.drop_table("kpi_rec_04")
    op.drop_table("kpi_rec_03")
    op.drop_table("kpi_rec_02")
    op.drop_table("kpi_rec_01")
    op.drop_table("kpi_not_03")
    op.drop_table("kpi_not_02")
    op.drop_table("kpi_not_01")
    op.drop_table("kpi_maj_04")
    op.drop_table("kpi_maj_03")
    op.drop_table("kpi_maj_02")
    op.drop_table("kpi_maj_01_national")
    op.drop_table("kpi_maj_01")
    op.drop_table("kpi_fsc_01")
    op.drop_table("kpi_ins_03_field")
    op.drop_table("kpi_ins_03")
    op.drop_table("kpi_ins_02_national")
    op.drop_table("kpi_ins_02")
    op.drop_table("kpi_ins_01")
    op.drop_table("kpi_acc_01")
    op.drop_table("kpi_geography")
    op.drop_table("kpi_imports")
