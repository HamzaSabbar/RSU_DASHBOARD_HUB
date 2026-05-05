from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ReportAmountRuleFact,
    ReportCodeFact,
    ReportFmsBlockedFact,
    ReportFmsTreatmentFact,
    ReportProgramFlowFact,
    ReportProgramFraudFact,
    ReportProgramRescoringFact,
    ReportProgramStockFact,
    ReportProvinceFact,
    ReportRegionFact,
    ReportRsuAnnotationFact,
    ReportRsuFlowFact,
    ReportRsuStockFact,
    ReportUploadBatch,
)
from reports import calculations
from reports.repository import ReportJobRecord
from reports.schemas import ValidationResult


async def active_batch_exists(session: AsyncSession, id_chargement: str) -> bool:
    existing = await session.scalar(
        select(ReportUploadBatch.id)
        .where(
            ReportUploadBatch.id_chargement == id_chargement,
            ReportUploadBatch.is_active.is_(True),
        )
        .limit(1)
    )
    return existing is not None


async def active_period_batch_exists(
    session: AsyncSession,
    *,
    systeme_source: str,
    period_start: date,
    period_end: date,
) -> bool:
    existing = await session.scalar(
        select(ReportUploadBatch.id)
        .where(
            _source_filter(systeme_source),
            ReportUploadBatch.period_start == period_start,
            ReportUploadBatch.period_end == period_end,
            ReportUploadBatch.is_active.is_(True),
        )
        .limit(1)
    )
    return existing is not None


async def ingest_report_batch(
    session: AsyncSession,
    *,
    record: ReportJobRecord,
    normalized: dict[str, Any],
) -> ReportUploadBatch:
    metadata = normalized.get("metadata", {})
    id_chargement = metadata.get("id_chargement") or record.id_chargement
    if not id_chargement:
        raise ValueError("id_chargement manquant pour l'ingestion cumulative")
    systeme_source = str(metadata.get("systeme_source") or "system")
    period_start = _date(metadata.get("debut_periode"))
    period_end = _date(metadata.get("fin_periode"))
    if period_start is None or period_end is None:
        raise ValueError("Période de chargement manquante pour l'ingestion cumulative")

    active_for_source = list(
        await session.scalars(
            select(ReportUploadBatch)
            .where(
                _source_filter(systeme_source),
                ReportUploadBatch.is_active.is_(True),
            )
            .with_for_update()
        )
    )
    exact_period = [
        batch
        for batch in active_for_source
        if batch.period_start == period_start and batch.period_end == period_end
    ]
    overlapping = [
        batch
        for batch in active_for_source
        if batch not in exact_period
        and batch.period_start is not None
        and batch.period_end is not None
        and _periods_overlap(period_start, period_end, batch.period_start, batch.period_end)
    ]
    if overlapping:
        raise ValueError(
            "Période de chargement chevauchante déjà active pour cette source. "
            "Corrigez ou remplacez la période existante avant d'importer ce fichier."
        )

    batch_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    for old_batch in exact_period:
        old_batch.status = "superseded"
        old_batch.is_active = False
        old_batch.superseded_at = now
    await session.flush()

    batch = ReportUploadBatch(
        id=batch_id,
        job_id=uuid.UUID(record.id),
        id_chargement=str(id_chargement),
        original_filename=record.original_filename,
        status="active",
        is_active=True,
        report_date=_date(metadata.get("date_rapport")),
        period_start=_date(metadata.get("debut_periode")),
        period_end=_date(metadata.get("fin_periode")),
        reference_date=_date(metadata.get("date_reference_donnees")),
        systeme_source=systeme_source,
        metadata_json=metadata,
        raw_object_path=record.raw_object_path,
        normalized_object_path=_required_path(record.normalized_object_path, "normalized"),
        validation_object_path=_required_path(record.validation_object_path, "validation"),
        dashboard_object_path=_required_path(record.dashboard_object_path, "dashboard"),
        uploaded_by=uuid.UUID(record.created_by) if record.created_by else None,
    )
    session.add(batch)
    await session.flush()
    for old_batch in exact_period:
        old_batch.superseded_by_batch_id = batch.id
    await session.flush()

    _add_reference_facts(session, batch, record, normalized)
    _add_rsu_facts(session, batch, record, normalized)
    _add_program_facts(session, batch, record, normalized)
    _add_fms_facts(session, batch, record, normalized)
    _add_amount_rules(session, batch, record, normalized)
    await session.flush()
    return batch


async def build_dashboard_for_range(
    session: AsyncSession,
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, Any]:
    normalized, resolved = await normalized_for_range(
        session,
        start_date=start_date,
        end_date=end_date,
    )
    dashboard = calculations.build_dashboard(
        normalized,
        job_id="cumulative",
        validation=ValidationResult(job_id="cumulative"),
    )
    dashboard.setdefault("meta", {})["dateRange"] = {
        "startDate": resolved["start"].isoformat(),
        "endDate": resolved["end"].isoformat(),
    }
    return dashboard


async def normalized_for_range(
    session: AsyncSession,
    *,
    start_date: date | None,
    end_date: date | None,
) -> tuple[dict[str, Any], dict[str, date]]:
    start, end, latest_batch = await _resolve_range(session, start_date, end_date)
    snapshot_batch = await _latest_snapshot_batch(session, start, end)
    metadata = dict(
        (snapshot_batch.metadata_json if snapshot_batch is not None else None)
        or latest_batch.metadata_json
        or {}
    )
    metadata.update(
        {
            "id_chargement": f"CUMUL_{start.isoformat()}_{end.isoformat()}",
            "date_rapport": end.isoformat(),
            "debut_periode": start.isoformat(),
            "fin_periode": end.isoformat(),
            "date_reference_donnees": (
                snapshot_batch.reference_date.isoformat()
                if snapshot_batch is not None and snapshot_batch.reference_date is not None
                else end.isoformat()
            ),
            "mois_reporting_courant": f"{end.year:04d}-{end.month:02d}",
        }
    )

    normalized: dict[str, Any] = {
        "metadata": metadata,
        "regions": await _regions(session),
        "provinces": await _provinces(session),
        "codes": await _codes(session),
        "rsu_stock": await _rsu_stock(session, snapshot_batch),
        "rsu_new_registrations": await _rsu_flow(session, start, end),
        "rsu_annotations": await _rsu_annotations(session, start, end),
        "asd_stock": await _program_stock(session, "ASD", snapshot_batch),
        "asd_flow": await _program_flow(session, "ASD", start, end),
        "asd_rescoring": await _program_rescoring(session, "ASD", start, end),
        "asd_fraud": await _program_fraud(session, "ASD", start, end),
        "amo_stock": await _program_stock(session, "AMO_TADAMON", snapshot_batch),
        "amo_flow": await _program_flow(session, "AMO_TADAMON", start, end),
        "amo_rescoring": await _program_rescoring(session, "AMO_TADAMON", start, end),
        "amo_fraud": await _program_fraud(session, "AMO_TADAMON", start, end),
        "fms_treatment": await _fms_treatment(session, start, end),
        "fms_blocked": await _fms_blocked(session, start, end),
        "amount_rules": await _amount_rules(session, end),
    }
    if not _normalized_has_dashboard_data(normalized):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune donnée disponible pour cette période.",
        )
    return normalized, {"start": start, "end": end}


async def available_periods(session: AsyncSession) -> dict[str, Any]:
    batches = list(
        await session.scalars(
            select(ReportUploadBatch)
            .where(ReportUploadBatch.is_active.is_(True))
            .order_by(
                ReportUploadBatch.reference_date.asc().nullslast(),
                ReportUploadBatch.created_at.asc(),
            )
        )
    )
    if not batches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport traité disponible.",
        )

    min_dates: list[date] = []
    max_dates: list[date] = []
    for model, field_name in (
        (ReportRsuFlowFact, "date_evenement"),
        (ReportProgramFlowFact, "date_evenement"),
        (ReportProgramRescoringFact, "date_evenement"),
        (ReportProgramFraudFact, "date_evenement"),
        (ReportFmsTreatmentFact, "date_evenement"),
        (ReportFmsBlockedFact, "date_evenement"),
        (ReportRsuStockFact, "date_reference"),
        (ReportProgramStockFact, "date_reference"),
    ):
        low, high = await _min_max_active(session, model, field_name)
        if low:
            min_dates.append(low)
        if high:
            max_dates.append(high)

    latest = _latest_batch(batches)
    return {
        "minDate": min(min_dates).isoformat() if min_dates else None,
        "maxDate": max(max_dates).isoformat() if max_dates else None,
        "latestReferenceDate": _iso(latest.reference_date),
        "latestReportDate": _iso(latest.report_date),
        "defaultStartDate": min(min_dates).isoformat() if min_dates else _iso(latest.period_start),
        "defaultEndDate": max(max_dates).isoformat() if max_dates else _iso(latest.period_end),
        "activeUploadBatches": [
            {
                "batchId": str(batch.id),
                "jobId": str(batch.job_id),
                "idChargement": batch.id_chargement,
                "dateRapport": _iso(batch.report_date),
                "debutPeriode": _iso(batch.period_start),
                "finPeriode": _iso(batch.period_end),
                "dateReferenceDonnees": _iso(batch.reference_date),
                "systemeSource": batch.systeme_source,
                "createdAt": batch.created_at.isoformat(),
            }
            for batch in batches
        ],
    }


def _normalized_has_dashboard_data(normalized: dict[str, Any]) -> bool:
    data_keys = (
        "rsu_stock",
        "rsu_new_registrations",
        "rsu_household_registrations",
        "asd_stock",
        "asd_flow",
        "asd_rescoring",
        "asd_fraud",
        "amo_stock",
        "amo_flow",
        "amo_rescoring",
        "amo_fraud",
        "fms_treatment",
        "fms_blocked",
    )
    return any(bool(normalized.get(key)) for key in data_keys)


def _add_reference_facts(
    session: AsyncSession,
    batch: ReportUploadBatch,
    record: ReportJobRecord,
    normalized: dict[str, Any],
) -> None:
    for row in normalized.get("regions", []):
        session.add(
            ReportRegionFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                code_region=str(row.get("code_region") or ""),
                nom_region=str(row.get("nom_region") or ""),
                ordre_affichage=row.get("ordre_affichage"),
            )
        )
    for row in normalized.get("provinces", []):
        session.add(
            ReportProvinceFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                code_region=str(row.get("code_region") or ""),
                nom_province=str(row.get("nom_province") or ""),
                ordre_affichage=row.get("ordre_affichage"),
            )
        )
    for row in normalized.get("codes", []):
        session.add(
            ReportCodeFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                type_code=str(row.get("type_code") or ""),
                code=str(row.get("code") or ""),
                libelle=row.get("libelle"),
                ordre_affichage=row.get("ordre_affichage"),
            )
        )


def _add_rsu_facts(
    session: AsyncSession,
    batch: ReportUploadBatch,
    record: ReportJobRecord,
    normalized: dict[str, Any],
) -> None:
    for row in normalized.get("rsu_stock", []):
        session.add(
            ReportRsuStockFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                date_reference=_required_date(row.get("date_reference")),
                code_registre=str(row.get("code_registre") or ""),
                type_unite=str(row.get("type_unite") or ""),
                total_cumule=int(row.get("total_cumule") or 0),
                systeme_source=row.get("systeme_source"),
                commentaires=row.get("commentaires"),
            )
        )
    registration_rows = [
        *normalized.get("rsu_new_registrations", []),
        *normalized.get("rsu_household_registrations", []),
    ]
    for row in registration_rows:
        session.add(
            ReportRsuFlowFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                debut_periode=_date(row.get("debut_periode")),
                fin_periode=_date(row.get("fin_periode")),
                date_evenement=_required_date(row.get("date_evenement")),
                mois_evenement=str(row.get("mois_evenement") or ""),
                code_region=row.get("code_region"),
                nom_province=row.get("nom_province"),
                code_registre=str(row.get("code_registre") or "RNP"),
                type_unite=str(row.get("type_unite") or ""),
                nb_nouvelles_inscriptions=int(row.get("nb_nouvelles_inscriptions") or 0),
                mode_source=row.get("mode_source"),
                systeme_source=row.get("systeme_source"),
                commentaires=row.get("commentaires"),
            )
        )
    for row in normalized.get("rsu_annotations", []):
        session.add(
            ReportRsuAnnotationFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                code_graphique=row.get("code_graphique"),
                mois_evenement=row.get("mois_evenement"),
                libelle_annotation=row.get("libelle_annotation"),
                commentaires=row.get("commentaires"),
            )
        )


def _add_program_facts(
    session: AsyncSession,
    batch: ReportUploadBatch,
    record: ReportJobRecord,
    normalized: dict[str, Any],
) -> None:
    for code, prefix in (("ASD", "asd"), ("AMO_TADAMON", "amo")):
        for row in normalized.get(f"{prefix}_stock", []):
            session.add(
                ReportProgramStockFact(
                    id=uuid.uuid4(),
                    batch_id=batch.id,
                    job_id=uuid.UUID(record.id),
                    source_row=_source_row(row),
                    code_programme=code,
                    date_reference=_required_date(row.get("date_reference")),
                    type_unite=str(row.get("type_unite") or ""),
                    nb_actifs=int(row.get("nb_actifs") or 0),
                    systeme_source=row.get("systeme_source"),
                    commentaires=row.get("commentaires"),
                )
            )
        for row in normalized.get(f"{prefix}_flow", []):
            session.add(
                ReportProgramFlowFact(
                    id=uuid.uuid4(),
                    batch_id=batch.id,
                    job_id=uuid.UUID(record.id),
                    source_row=_source_row(row),
                    code_programme=code,
                    debut_periode=_date(row.get("debut_periode")),
                    fin_periode=_date(row.get("fin_periode")),
                    date_evenement=_required_date(row.get("date_evenement")),
                    mois_evenement=str(row.get("mois_evenement") or ""),
                    code_region=row.get("code_region"),
                    nom_province=row.get("nom_province"),
                    nb_entrants_menages=int(row.get("nb_entrants_menages") or 0),
                    nb_sortants_menages=int(row.get("nb_sortants_menages") or 0),
                    nb_entrants_personnes=int(row.get("nb_entrants_personnes") or 0),
                    nb_sortants_personnes=int(row.get("nb_sortants_personnes") or 0),
                    montant_mensuel_entrants_dh=row.get("montant_mensuel_entrants_dh"),
                    montant_mensuel_sortants_dh=row.get("montant_mensuel_sortants_dh"),
                    systeme_source=row.get("systeme_source"),
                    commentaires=row.get("commentaires"),
                )
            )
        for row in normalized.get(f"{prefix}_rescoring", []):
            session.add(
                ReportProgramRescoringFact(
                    id=uuid.uuid4(),
                    batch_id=batch.id,
                    job_id=uuid.UUID(record.id),
                    source_row=_source_row(row),
                    code_programme=code,
                    debut_periode=_date(row.get("debut_periode")),
                    fin_periode=_date(row.get("fin_periode")),
                    date_evenement=_required_date(row.get("date_evenement")),
                    mois_evenement=str(row.get("mois_evenement") or ""),
                    code_region=row.get("code_region"),
                    nom_province=row.get("nom_province"),
                    nb_sortants_menages=int(row.get("nb_sortants_menages") or 0),
                    nb_sortants_personnes=int(row.get("nb_sortants_personnes") or 0),
                    nb_menages_non_communiques=int(row.get("nb_menages_non_communiques") or 0),
                    montant_mensuel_arrete_dh=row.get("montant_mensuel_arrete_dh"),
                    systeme_source=row.get("systeme_source"),
                    commentaires=row.get("commentaires"),
                )
            )
        for row in normalized.get(f"{prefix}_fraud", []):
            session.add(
                ReportProgramFraudFact(
                    id=uuid.uuid4(),
                    batch_id=batch.id,
                    job_id=uuid.UUID(record.id),
                    source_row=_source_row(row),
                    code_programme=code,
                    debut_periode=_date(row.get("debut_periode")),
                    fin_periode=_date(row.get("fin_periode")),
                    date_evenement=_required_date(row.get("date_evenement")),
                    mois_evenement=str(row.get("mois_evenement") or ""),
                    code_region=row.get("code_region"),
                    nom_province=row.get("nom_province"),
                    radiated_hh_count=int(row.get("radiated_hh_count") or 0),
                    radiated_persons=int(row.get("radiated_persons") or 0),
                    montant_mensuel_arrete_dh=row.get("montant_mensuel_arrete_dh"),
                    systeme_source=row.get("systeme_source"),
                    commentaires=row.get("commentaires"),
                )
            )


def _add_fms_facts(
    session: AsyncSession,
    batch: ReportUploadBatch,
    record: ReportJobRecord,
    normalized: dict[str, Any],
) -> None:
    for row in normalized.get("fms_treatment", []):
        session.add(
            ReportFmsTreatmentFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                date_reference=_required_date(row.get("date_reference")),
                debut_periode=_date(row.get("debut_periode")),
                fin_periode=_date(row.get("fin_periode")),
                date_evenement=_date(row.get("date_evenement")),
                mois_evenement=row.get("mois_evenement"),
                code_type_famille=str(row.get("code_type_famille") or ""),
                code_niveau_risque=str(row.get("code_niveau_risque") or ""),
                code_perimetre_programme=row.get("code_perimetre_programme"),
                code_region=row.get("code_region"),
                nom_province=row.get("nom_province"),
                demandes_injectees=int(row.get("demandes_injectees") or 0),
                demandes_traitees=int(row.get("demandes_traitees") or 0),
                doute_confirme=int(row.get("doute_confirme") or 0),
                doute_leve=int(row.get("doute_leve") or 0),
                en_attente=int(row.get("en_attente") or 0),
                systeme_source=row.get("systeme_source"),
                commentaires=row.get("commentaires"),
            )
        )
    for row in normalized.get("fms_blocked", []):
        session.add(
            ReportFmsBlockedFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                date_reference=_required_date(row.get("date_reference")),
                debut_periode=_date(row.get("debut_periode")),
                fin_periode=_date(row.get("fin_periode")),
                date_evenement=_date(row.get("date_evenement")),
                mois_evenement=row.get("mois_evenement"),
                code_motif_blocage=str(row.get("code_motif_blocage") or ""),
                code_type_famille=row.get("code_type_famille"),
                code_region=row.get("code_region"),
                nom_province=row.get("nom_province"),
                nb_menages_bloques=int(row.get("nb_menages_bloques") or 0),
                nb_personnes_bloquees=int(row.get("nb_personnes_bloquees") or 0),
                systeme_source=row.get("systeme_source"),
                commentaires=row.get("commentaires"),
            )
        )


def _add_amount_rules(
    session: AsyncSession,
    batch: ReportUploadBatch,
    record: ReportJobRecord,
    normalized: dict[str, Any],
) -> None:
    for row in normalized.get("amount_rules", []):
        session.add(
            ReportAmountRuleFact(
                id=uuid.uuid4(),
                batch_id=batch.id,
                job_id=uuid.UUID(record.id),
                source_row=_source_row(row),
                code_programme=str(row.get("code_programme") or ""),
                date_effet_debut=_required_date(row.get("date_effet_debut")),
                date_effet_fin=_date(row.get("date_effet_fin")),
                code_type_famille=row.get("code_type_famille"),
                unite_beneficiaire=row.get("unite_beneficiaire"),
                type_montant=row.get("type_montant"),
                montant_mensuel_dh=float(row.get("montant_mensuel_dh") or 0),
                facteur_annualisation=float(row.get("facteur_annualisation") or 12),
                commentaires=row.get("commentaires"),
            )
        )


def _periods_overlap(
    start_a: date,
    end_a: date,
    start_b: date,
    end_b: date,
) -> bool:
    return start_a <= end_b and start_b <= end_a


def _source_filter(systeme_source: str):
    if systeme_source == "system":
        return or_(
            ReportUploadBatch.systeme_source == systeme_source,
            ReportUploadBatch.systeme_source.is_(None),
        )
    return ReportUploadBatch.systeme_source == systeme_source


async def _resolve_range(
    session: AsyncSession,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date, ReportUploadBatch]:
    latest = await session.scalar(
        select(ReportUploadBatch)
        .where(ReportUploadBatch.is_active.is_(True))
        .order_by(
            ReportUploadBatch.reference_date.desc().nullslast(),
            ReportUploadBatch.report_date.desc().nullslast(),
            ReportUploadBatch.created_at.desc(),
        )
        .limit(1)
    )
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun rapport traité disponible.",
        )

    available = await available_periods(session)
    min_date = _date(available.get("minDate"))
    max_date = _date(available.get("maxDate"))
    if start_date is None and end_date is None:
        start = min_date or latest.period_start or latest.reference_date or latest.report_date
        end = max_date or latest.period_end or latest.reference_date or latest.report_date
    else:
        end = end_date or max_date or latest.period_end or latest.reference_date or latest.report_date
        start = start_date or min_date or end
    if start is None or end is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune date exploitable disponible.",
        )
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="startDate doit être inférieure ou égale à endDate.",
        )
    return start, end, latest


async def _latest_snapshot_batch(
    session: AsyncSession,
    start: date,
    end: date,
) -> ReportUploadBatch | None:
    batch = await session.scalar(
        select(ReportUploadBatch)
        .where(
            ReportUploadBatch.is_active.is_(True),
            ReportUploadBatch.reference_date >= start,
            ReportUploadBatch.reference_date <= end,
        )
        .order_by(ReportUploadBatch.reference_date.desc(), ReportUploadBatch.created_at.desc())
        .limit(1)
    )
    return batch


async def _regions(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await _active_rows(session, ReportRegionFact)
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedup[row.code_region] = {
            "_row": row.source_row,
            "code_region": row.code_region,
            "nom_region": row.nom_region,
            "ordre_affichage": row.ordre_affichage,
        }
    return list(dedup.values())


async def _provinces(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await _active_rows(session, ReportProvinceFact)
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        dedup[(row.code_region, row.nom_province)] = {
            "_row": row.source_row,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "ordre_affichage": row.ordre_affichage,
        }
    return list(dedup.values())


async def _codes(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await _active_rows(session, ReportCodeFact)
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        dedup[(row.type_code, row.code)] = {
            "_row": row.source_row,
            "type_code": row.type_code,
            "code": row.code,
            "libelle": row.libelle,
            "ordre_affichage": row.ordre_affichage,
        }
    return list(dedup.values())


async def _rsu_stock(
    session: AsyncSession,
    snapshot_batch: ReportUploadBatch | None,
) -> list[dict[str, Any]]:
    if snapshot_batch is None:
        return []
    rows = await _active_rows(
        session,
        ReportRsuStockFact,
        ReportRsuStockFact.batch_id == snapshot_batch.id,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "date_reference": _iso(row.date_reference),
            "code_registre": row.code_registre,
            "type_unite": row.type_unite,
            "total_cumule": row.total_cumule,
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _rsu_flow(session: AsyncSession, start: date, end: date) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportRsuFlowFact,
        ReportRsuFlowFact.date_evenement >= start,
        ReportRsuFlowFact.date_evenement <= end,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "debut_periode": _iso(row.debut_periode),
            "fin_periode": _iso(row.fin_periode),
            "date_evenement": _iso(row.date_evenement),
            "mois_evenement": row.mois_evenement,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "code_registre": row.code_registre,
            "type_unite": row.type_unite,
            "nb_nouvelles_inscriptions": row.nb_nouvelles_inscriptions,
            "mode_source": row.mode_source,
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _rsu_annotations(session: AsyncSession, start: date, end: date) -> list[dict[str, Any]]:
    start_month = f"{start.year:04d}-{start.month:02d}"
    end_month = f"{end.year:04d}-{end.month:02d}"
    rows = await _active_rows(
        session,
        ReportRsuAnnotationFact,
        ReportRsuAnnotationFact.mois_evenement >= start_month,
        ReportRsuAnnotationFact.mois_evenement <= end_month,
    )
    return [
        {
            "_row": row.source_row,
            "code_graphique": row.code_graphique,
            "mois_evenement": row.mois_evenement,
            "libelle_annotation": row.libelle_annotation,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _program_stock(
    session: AsyncSession,
    programme: str,
    snapshot_batch: ReportUploadBatch | None,
) -> list[dict[str, Any]]:
    if snapshot_batch is None:
        return []
    rows = await _active_rows(
        session,
        ReportProgramStockFact,
        ReportProgramStockFact.code_programme == programme,
        ReportProgramStockFact.batch_id == snapshot_batch.id,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "date_reference": _iso(row.date_reference),
            "type_unite": row.type_unite,
            "nb_actifs": row.nb_actifs,
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _program_flow(
    session: AsyncSession,
    programme: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportProgramFlowFact,
        ReportProgramFlowFact.code_programme == programme,
        ReportProgramFlowFact.date_evenement >= start,
        ReportProgramFlowFact.date_evenement <= end,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "debut_periode": _iso(row.debut_periode),
            "fin_periode": _iso(row.fin_periode),
            "date_evenement": _iso(row.date_evenement),
            "mois_evenement": row.mois_evenement,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "nb_entrants_menages": row.nb_entrants_menages,
            "nb_sortants_menages": row.nb_sortants_menages,
            "nb_entrants_personnes": row.nb_entrants_personnes,
            "nb_sortants_personnes": row.nb_sortants_personnes,
            "montant_mensuel_entrants_dh": _float(row.montant_mensuel_entrants_dh),
            "montant_mensuel_sortants_dh": _float(row.montant_mensuel_sortants_dh),
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _program_rescoring(
    session: AsyncSession,
    programme: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportProgramRescoringFact,
        ReportProgramRescoringFact.code_programme == programme,
        ReportProgramRescoringFact.date_evenement >= start,
        ReportProgramRescoringFact.date_evenement <= end,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "debut_periode": _iso(row.debut_periode),
            "fin_periode": _iso(row.fin_periode),
            "date_evenement": _iso(row.date_evenement),
            "mois_evenement": row.mois_evenement,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "nb_sortants_menages": row.nb_sortants_menages,
            "nb_sortants_personnes": row.nb_sortants_personnes,
            "nb_menages_non_communiques": row.nb_menages_non_communiques,
            "montant_mensuel_arrete_dh": _float(row.montant_mensuel_arrete_dh),
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _program_fraud(
    session: AsyncSession,
    programme: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportProgramFraudFact,
        ReportProgramFraudFact.code_programme == programme,
        ReportProgramFraudFact.date_evenement >= start,
        ReportProgramFraudFact.date_evenement <= end,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "debut_periode": _iso(row.debut_periode),
            "fin_periode": _iso(row.fin_periode),
            "date_evenement": _iso(row.date_evenement),
            "mois_evenement": row.mois_evenement,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "radiated_hh_count": row.radiated_hh_count,
            "radiated_persons": row.radiated_persons,
            "montant_mensuel_arrete_dh": _float(row.montant_mensuel_arrete_dh),
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _fms_treatment(
    session: AsyncSession,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportFmsTreatmentFact,
        ReportFmsTreatmentFact.date_evenement >= start,
        ReportFmsTreatmentFact.date_evenement <= end,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "date_reference": _iso(row.date_reference),
            "debut_periode": _iso(row.debut_periode),
            "fin_periode": _iso(row.fin_periode),
            "date_evenement": _iso(row.date_evenement),
            "mois_evenement": row.mois_evenement,
            "code_type_famille": row.code_type_famille,
            "code_niveau_risque": row.code_niveau_risque,
            "code_perimetre_programme": row.code_perimetre_programme,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "demandes_injectees": row.demandes_injectees,
            "demandes_traitees": row.demandes_traitees,
            "doute_confirme": row.doute_confirme,
            "doute_leve": row.doute_leve,
            "en_attente": row.en_attente,
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _fms_blocked(
    session: AsyncSession,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportFmsBlockedFact,
        ReportFmsBlockedFact.date_evenement >= start,
        ReportFmsBlockedFact.date_evenement <= end,
    )
    return [
        {
            "_row": row.source_row,
            "id_chargement": "",
            "date_reference": _iso(row.date_reference),
            "debut_periode": _iso(row.debut_periode),
            "fin_periode": _iso(row.fin_periode),
            "date_evenement": _iso(row.date_evenement),
            "mois_evenement": row.mois_evenement,
            "code_motif_blocage": row.code_motif_blocage,
            "code_type_famille": row.code_type_famille,
            "code_region": row.code_region,
            "nom_province": row.nom_province,
            "nb_menages_bloques": row.nb_menages_bloques,
            "nb_personnes_bloquees": row.nb_personnes_bloquees,
            "systeme_source": row.systeme_source,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _amount_rules(session: AsyncSession, end: date) -> list[dict[str, Any]]:
    rows = await _active_rows(
        session,
        ReportAmountRuleFact,
        ReportAmountRuleFact.date_effet_debut <= end,
    )
    return [
        {
            "_row": row.source_row,
            "code_programme": row.code_programme,
            "date_effet_debut": _iso(row.date_effet_debut),
            "date_effet_fin": _iso(row.date_effet_fin),
            "code_type_famille": row.code_type_famille,
            "unite_beneficiaire": row.unite_beneficiaire,
            "type_montant": row.type_montant,
            "montant_mensuel_dh": _float(row.montant_mensuel_dh) or 0,
            "facteur_annualisation": _float(row.facteur_annualisation) or 12,
            "commentaires": row.commentaires,
        }
        for row in rows
    ]


async def _active_rows(
    session: AsyncSession,
    model: Any,
    *conditions: Any,
) -> list[Any]:
    stmt = (
        select(model)
        .join(ReportUploadBatch, model.batch_id == ReportUploadBatch.id)
        .where(ReportUploadBatch.is_active.is_(True), *conditions)
        .order_by(ReportUploadBatch.created_at.asc())
    )
    return list(await session.scalars(stmt))


async def _min_max_active(
    session: AsyncSession,
    model: type[Any],
    field_name: str,
) -> tuple[date | None, date | None]:
    field = getattr(model, field_name)
    row = await session.execute(
        select(func.min(field), func.max(field))
        .select_from(model)
        .join(ReportUploadBatch, model.batch_id == ReportUploadBatch.id)
        .where(ReportUploadBatch.is_active.is_(True))
    )
    low, high = row.one()
    return low, high


def _latest_batch(batches: Iterable[ReportUploadBatch]) -> ReportUploadBatch:
    return sorted(
        batches,
        key=lambda batch: (
            batch.reference_date or date.min,
            batch.report_date or date.min,
            batch.created_at,
        ),
    )[-1]


def _required_path(path: str | None, label: str) -> str:
    if not path:
        raise ValueError(f"Chemin d'artifact manquant: {label}")
    return path


def _required_date(value: Any) -> date:
    parsed = _date(value)
    if parsed is None:
        raise ValueError(f"Date obligatoire invalide: {value}")
    return parsed


def _date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _source_row(row: dict[str, Any]) -> int | None:
    value = row.get("_row")
    return int(value) if value is not None else None


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
