"""cumulative report batches and fact tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-27

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fact_base() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_upload_batches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_row", sa.Integer(), nullable=True),
    ]


def upgrade() -> None:
    op.add_column(
        "report_jobs",
        sa.Column(
            "replace_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("report_jobs", "replace_requested", server_default=None)

    op.create_table(
        "report_upload_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_jobs.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("id_chargement", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_object_path", sa.String(length=1024), nullable=False),
        sa.Column("normalized_object_path", sa.String(length=1024), nullable=False),
        sa.Column("validation_object_path", sa.String(length=1024), nullable=False),
        sa.Column("dashboard_object_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "superseded_by_batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_upload_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded')",
            name="report_upload_batches_status_check",
        ),
    )
    op.create_index("ix_report_upload_batches_job_id", "report_upload_batches", ["job_id"])
    op.create_index("ix_report_upload_batches_created_at", "report_upload_batches", ["created_at"])
    op.create_index("ix_report_upload_batches_status", "report_upload_batches", ["status"])
    op.create_index("ix_report_upload_batches_is_active", "report_upload_batches", ["is_active"])
    op.create_index("ix_report_upload_batches_id_chargement", "report_upload_batches", ["id_chargement"])
    op.create_index("ix_report_upload_batches_report_date", "report_upload_batches", ["report_date"])
    op.create_index("ix_report_upload_batches_period_start", "report_upload_batches", ["period_start"])
    op.create_index("ix_report_upload_batches_period_end", "report_upload_batches", ["period_end"])
    op.create_index("ix_report_upload_batches_reference_date", "report_upload_batches", ["reference_date"])
    op.create_index(
        "ix_report_upload_batches_active_id_chargement",
        "report_upload_batches",
        ["id_chargement"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )

    op.create_table(
        "report_regions",
        *_fact_base(),
        sa.Column("code_region", sa.String(length=64), nullable=False),
        sa.Column("nom_region", sa.String(length=255), nullable=False),
        sa.Column("ordre_affichage", sa.Integer(), nullable=True),
    )
    op.create_table(
        "report_provinces",
        *_fact_base(),
        sa.Column("code_region", sa.String(length=64), nullable=False),
        sa.Column("nom_province", sa.String(length=255), nullable=False),
        sa.Column("ordre_affichage", sa.Integer(), nullable=True),
    )
    op.create_table(
        "report_codes",
        *_fact_base(),
        sa.Column("type_code", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("libelle", sa.String(length=512), nullable=True),
        sa.Column("ordre_affichage", sa.Integer(), nullable=True),
    )
    op.create_table(
        "report_rsu_stock",
        *_fact_base(),
        sa.Column("date_reference", sa.Date(), nullable=False),
        sa.Column("code_registre", sa.String(length=64), nullable=False),
        sa.Column("type_unite", sa.String(length=64), nullable=False),
        sa.Column("total_cumule", sa.Integer(), nullable=False),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_rsu_flow",
        *_fact_base(),
        sa.Column("debut_periode", sa.Date(), nullable=True),
        sa.Column("fin_periode", sa.Date(), nullable=True),
        sa.Column("date_evenement", sa.Date(), nullable=False),
        sa.Column("mois_evenement", sa.String(length=7), nullable=False),
        sa.Column("code_region", sa.String(length=64), nullable=True),
        sa.Column("nom_province", sa.String(length=255), nullable=True),
        sa.Column("type_unite", sa.String(length=64), nullable=False),
        sa.Column("nb_nouvelles_inscriptions", sa.Integer(), nullable=False),
        sa.Column("mode_source", sa.String(length=128), nullable=True),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_rsu_annotations",
        *_fact_base(),
        sa.Column("code_graphique", sa.String(length=128), nullable=True),
        sa.Column("mois_evenement", sa.String(length=7), nullable=True),
        sa.Column("libelle_annotation", sa.Text(), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_program_stock",
        *_fact_base(),
        sa.Column("code_programme", sa.String(length=64), nullable=False),
        sa.Column("date_reference", sa.Date(), nullable=False),
        sa.Column("type_unite", sa.String(length=64), nullable=False),
        sa.Column("nb_actifs", sa.Integer(), nullable=False),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_program_flow",
        *_fact_base(),
        sa.Column("code_programme", sa.String(length=64), nullable=False),
        sa.Column("debut_periode", sa.Date(), nullable=True),
        sa.Column("fin_periode", sa.Date(), nullable=True),
        sa.Column("date_evenement", sa.Date(), nullable=False),
        sa.Column("mois_evenement", sa.String(length=7), nullable=False),
        sa.Column("code_region", sa.String(length=64), nullable=True),
        sa.Column("nom_province", sa.String(length=255), nullable=True),
        sa.Column("nb_entrants_menages", sa.Integer(), nullable=False),
        sa.Column("nb_sortants_menages", sa.Integer(), nullable=False),
        sa.Column("nb_entrants_personnes", sa.Integer(), nullable=False),
        sa.Column("nb_sortants_personnes", sa.Integer(), nullable=False),
        sa.Column("montant_mensuel_entrants_dh", sa.Numeric(18, 2), nullable=True),
        sa.Column("montant_mensuel_sortants_dh", sa.Numeric(18, 2), nullable=True),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_program_rescoring",
        *_fact_base(),
        sa.Column("code_programme", sa.String(length=64), nullable=False),
        sa.Column("debut_periode", sa.Date(), nullable=True),
        sa.Column("fin_periode", sa.Date(), nullable=True),
        sa.Column("date_evenement", sa.Date(), nullable=False),
        sa.Column("mois_evenement", sa.String(length=7), nullable=False),
        sa.Column("code_region", sa.String(length=64), nullable=True),
        sa.Column("nom_province", sa.String(length=255), nullable=True),
        sa.Column("nb_sortants_menages", sa.Integer(), nullable=False),
        sa.Column("nb_sortants_personnes", sa.Integer(), nullable=False),
        sa.Column("nb_menages_non_communiques", sa.Integer(), nullable=False),
        sa.Column("montant_mensuel_arrete_dh", sa.Numeric(18, 2), nullable=True),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_program_fraud",
        *_fact_base(),
        sa.Column("code_programme", sa.String(length=64), nullable=False),
        sa.Column("debut_periode", sa.Date(), nullable=True),
        sa.Column("fin_periode", sa.Date(), nullable=True),
        sa.Column("date_evenement", sa.Date(), nullable=False),
        sa.Column("mois_evenement", sa.String(length=7), nullable=False),
        sa.Column("code_region", sa.String(length=64), nullable=True),
        sa.Column("nom_province", sa.String(length=255), nullable=True),
        sa.Column("radiated_hh_count", sa.Integer(), nullable=False),
        sa.Column("radiated_persons", sa.Integer(), nullable=False),
        sa.Column("montant_mensuel_arrete_dh", sa.Numeric(18, 2), nullable=True),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_fms_treatment",
        *_fact_base(),
        sa.Column("date_reference", sa.Date(), nullable=False),
        sa.Column("code_type_famille", sa.String(length=128), nullable=False),
        sa.Column("code_niveau_risque", sa.String(length=128), nullable=False),
        sa.Column("code_perimetre_programme", sa.String(length=128), nullable=True),
        sa.Column("code_region", sa.String(length=64), nullable=True),
        sa.Column("nom_province", sa.String(length=255), nullable=True),
        sa.Column("demandes_injectees", sa.Integer(), nullable=False),
        sa.Column("demandes_traitees", sa.Integer(), nullable=False),
        sa.Column("doute_confirme", sa.Integer(), nullable=False),
        sa.Column("doute_leve", sa.Integer(), nullable=False),
        sa.Column("en_attente", sa.Integer(), nullable=False),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_fms_blocked",
        *_fact_base(),
        sa.Column("date_reference", sa.Date(), nullable=False),
        sa.Column("code_motif_blocage", sa.String(length=128), nullable=False),
        sa.Column("code_type_famille", sa.String(length=128), nullable=True),
        sa.Column("code_region", sa.String(length=64), nullable=True),
        sa.Column("nom_province", sa.String(length=255), nullable=True),
        sa.Column("nb_menages_bloques", sa.Integer(), nullable=False),
        sa.Column("nb_personnes_bloquees", sa.Integer(), nullable=False),
        sa.Column("systeme_source", sa.String(length=255), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )
    op.create_table(
        "report_amount_rules",
        *_fact_base(),
        sa.Column("code_programme", sa.String(length=64), nullable=False),
        sa.Column("date_effet_debut", sa.Date(), nullable=False),
        sa.Column("date_effet_fin", sa.Date(), nullable=True),
        sa.Column("code_type_famille", sa.String(length=128), nullable=True),
        sa.Column("unite_beneficiaire", sa.String(length=128), nullable=True),
        sa.Column("type_montant", sa.String(length=128), nullable=True),
        sa.Column("montant_mensuel_dh", sa.Numeric(18, 2), nullable=False),
        sa.Column("facteur_annualisation", sa.Numeric(8, 2), nullable=False),
        sa.Column("commentaires", sa.Text(), nullable=True),
    )

    _index_common("report_regions", ["code_region"])
    _index_common("report_provinces", ["code_region", "nom_province"])
    _index_common("report_codes", ["type_code", "code"])
    _index_common("report_rsu_stock", ["date_reference", "code_registre", "type_unite"])
    _index_common("report_rsu_flow", ["date_evenement", "mois_evenement", "code_region", "nom_province"])
    _index_common("report_rsu_annotations", ["mois_evenement"])
    _index_common("report_program_stock", ["code_programme", "date_reference", "type_unite"])
    _index_common("report_program_flow", ["code_programme", "date_evenement", "code_region", "nom_province"])
    _index_common("report_program_rescoring", ["code_programme", "date_evenement", "code_region", "nom_province"])
    _index_common("report_program_fraud", ["code_programme", "date_evenement", "code_region", "nom_province"])
    _index_common("report_fms_treatment", ["date_reference", "code_region", "nom_province"])
    _index_common("report_fms_blocked", ["date_reference", "code_region", "nom_province"])
    _index_common("report_amount_rules", ["code_programme", "date_effet_debut", "date_effet_fin"])


def downgrade() -> None:
    for table in (
        "report_amount_rules",
        "report_fms_blocked",
        "report_fms_treatment",
        "report_program_fraud",
        "report_program_rescoring",
        "report_program_flow",
        "report_program_stock",
        "report_rsu_annotations",
        "report_rsu_flow",
        "report_rsu_stock",
        "report_codes",
        "report_provinces",
        "report_regions",
    ):
        op.drop_table(table)

    op.drop_index("ix_report_upload_batches_active_id_chargement", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_reference_date", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_period_end", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_period_start", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_report_date", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_id_chargement", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_is_active", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_status", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_created_at", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_job_id", table_name="report_upload_batches")
    op.drop_table("report_upload_batches")
    op.drop_column("report_jobs", "replace_requested")


def _index_common(table: str, fields: list[str]) -> None:
    op.create_index(f"ix_{table}_batch_id", table, ["batch_id"])
    op.create_index(f"ix_{table}_job_id", table, ["job_id"])
    for field in fields:
        op.create_index(f"ix_{table}_{field}", table, [field])
