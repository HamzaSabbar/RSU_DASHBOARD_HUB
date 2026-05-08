from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from reports.schemas import ValidationResult

FR_MONTHS = {
    1: "janv.",
    2: "févr.",
    3: "mars",
    4: "avr.",
    5: "mai",
    6: "juin",
    7: "juil.",
    8: "août",
    9: "sept.",
    10: "oct.",
    11: "nov.",
    12: "déc.",
}


def build_dashboard(
    normalized: dict[str, Any],
    *,
    job_id: str,
    validation: ValidationResult,
) -> dict[str, Any]:
    metadata = normalized.get("metadata", {})
    code_labels = _code_labels(normalized)
    regions = _ordered_regions(normalized)
    reference_date = metadata.get("date_reference_donnees")
    current_month = _current_month(metadata, normalized)
    previous_month = _previous_month(current_month, _all_flow_months(normalized))

    rsu_graph_unit = _rsu_graph_unit(normalized)
    rsu_monthly = _rsu_monthly_values(normalized, graph_unit=rsu_graph_unit)
    rsu_evolution = _monthly_evolution(
        rsu_monthly,
        current_month=current_month,
        partial_suffix=metadata.get("suffixe_libelle_mois_partiel") or "(partiel)",
        is_partial=bool(metadata.get("indicateur_mois_partiel")),
    )
    trend = _trend_series(
        rsu_monthly,
        method=str(metadata.get("methode_tendance") or "AUCUNE"),
    )

    asd_monthly = _program_monthly(normalized.get("asd_flow", []))
    asd_evolution = _program_comparison(asd_monthly, current_month, previous_month)
    combined_region_flux = _combined_region_flux(normalized, None, regions)
    top_flux = _top_province_flux(normalized, None)

    fms_rows = normalized.get("fms_treatment", [])
    fms_totals = _fms_totals(fms_rows)
    fms_matrix = _fms_matrix(fms_rows, code_labels)

    blocked_rows = normalized.get("fms_blocked", [])
    blocked_national = _blocked_by_reason(blocked_rows, code_labels)
    blocked_regional = _blocked_by_region(blocked_rows, regions)
    top_blocked = _top_blocked_provinces(blocked_rows)

    fraud = _fraud_summary(normalized, reference_date)
    rescoring = _rescoring_summary(normalized, reference_date)
    budget_total = fraud["savingAnnualRaw"] + rescoring["savingAnnualRaw"]
    asd_personnes_total = _program_active_total(
        normalized.get("asd_flow", []),
        normalized.get("asd_stock", []),
        reference_date,
        type_unite="PERSONNES",
    )
    rsu_personnes_total = _registration_total(
        normalized,
        code_registre="RSU",
        type_unite="PERSONNES",
        fallback_stock_field="total_cumule",
        reference_date=reference_date,
    )
    amo_personnes_total = _program_active_total(
        normalized.get("amo_flow", []),
        normalized.get("amo_stock", []),
        reference_date,
        type_unite="PERSONNES",
    )

    dashboard = {
        "meta": {
            "jobId": job_id,
            "idChargement": metadata.get("id_chargement"),
            "titreRapport": "Tableau de bord cumulatif de suivi RSU",
            "dateRapport": metadata.get("date_rapport"),
            "dateReferenceDonnees": reference_date,
            "locale": "fr-MA",
            "moisReportingCourant": current_month,
            "moisPartiel": bool(metadata.get("indicateur_mois_partiel")),
            "terminologie": {
                "RSU": "Registre Social Unifié",
                "RNP": "Registre National de la Population",
                "ASD": "Aide Sociale Directe",
                "AMO_TADAMON": "AMO Tadamon",
                "FMS": "Fraud Management System",
            },
        },
        "layout": {
            "palette": {
                "positive": "green",
                "main": "green",
                "risk": "red",
                "exit": "red",
                "neutral": "gray",
            },
            "regionOrder": [region["code_region"] for region in regions],
        },
        "cards": {
            "inscriptions": _without_empty_metrics({
                "title": "Chiffres clés des inscriptions",
                "rnpPersonnesTotal": _metric(
                    "Personnes inscrites",
                    _registration_total(
                        normalized,
                        code_registre="RNP",
                        type_unite="PERSONNES",
                        fallback_stock_field="total_cumule",
                        reference_date=reference_date,
                    ),
                    color="green",
                ),
                "rsuMenagesTotal": _metric(
                    "Ménages inscrits",
                    _registration_total(
                        normalized,
                        code_registre="RSU",
                        type_unite="MENAGES",
                        fallback_stock_field="total_cumule",
                        reference_date=reference_date,
                    ),
                    color="green",
                ),
                "rsuPersonnesCouvertes": _optional_positive_metric(
                    "Personnes couvertes RSU",
                    rsu_personnes_total,
                    color="green",
                ),
                "nouvellesInscriptionsMois": _metric(
                    "Nouvelles inscriptions RSU",
                    rsu_monthly.get(current_month, 0),
                    color="green",
                ),
                "evolutionMois": _delta_metric(
                    "Évolution vs mois précédent",
                    rsu_monthly.get(current_month, 0) - rsu_monthly.get(previous_month, 0),
                    rsu_monthly.get(previous_month, 0),
                ),
            }),
            "programmesSociaux": _without_empty_metrics({
                "title": "Programmes sociaux",
                "asdMenagesActifs": _metric(
                    "Ménages ASD",
                    _program_active_total(
                        normalized.get("asd_flow", []),
                        normalized.get("asd_stock", []),
                        reference_date,
                        type_unite="MENAGES",
                    ),
                    color="green",
                ),
                "asdPersonnesActives": _optional_positive_metric(
                    "ASD - personnes net cumulées",
                    asd_personnes_total,
                    color="green",
                ),
                "amoMenagesActifs": _metric(
                    "Ménages AMO Tadamon",
                    _program_active_total(
                        normalized.get("amo_flow", []),
                        normalized.get("amo_stock", []),
                        reference_date,
                        type_unite="MENAGES",
                    ),
                    color="green",
                ),
                "amoPersonnesActives": _optional_positive_metric(
                    "AMO Tadamon - personnes net cumulées",
                    amo_personnes_total,
                    color="green",
                ),
            }),
            "traitementFms": {
                "title": "Traitement FMS",
                "demandesInjectees": _metric("Demandes injectées", fms_totals["injected"]),
                "demandesTraitees": _metric("Demandes traitées", fms_totals["processed"]),
                "tauxTraitementPct": _percent_metric(
                    "Taux de traitement",
                    _ratio(fms_totals["processed"], fms_totals["injected"]),
                ),
            },
            "resultatFms": {
                "title": "Résultat FMS",
                "douteConfirme": _metric("Doute confirmé", fms_totals["confirmed"], color="red"),
                "douteConfirmePct": _percent_metric(
                    "Doute confirmé",
                    _ratio(fms_totals["confirmed"], fms_totals["processed"]),
                    color="red",
                ),
                "douteLeve": _metric("Doute levé", fms_totals["cleared"]),
                "douteLevePct": _percent_metric(
                    "Doute levé",
                    _ratio(fms_totals["cleared"], fms_totals["processed"]),
                ),
            },
            "radiationFraude": fraud,
            "rescoring": rescoring,
            "economieBudgetaire": {
                "title": "Économie budgétaire totale",
                "fraude": _money_metric("Fraude", fraud["savingAnnualRaw"], color="red"),
                "rescoring": _money_metric("Rescoring", rescoring["savingAnnualRaw"]),
                "total": _money_metric("Total optimisation", budget_total, color="green"),
            },
        },
        "charts": {
            "rsuInscriptionsMensuelles": {
                "title": "Dynamique des inscriptions au RSU",
                "unit": rsu_graph_unit,
                "series": [
                    {
                        "month": point["month"],
                        "label": point["label"],
                        "raw": point["raw"],
                        "display": _format_number(point["raw"]),
                    }
                    for point in rsu_evolution
                ],
                "trend": trend,
                "color": "green",
            },
            "asdEntreesSorties": {
                "title": "Dynamique d’entrées / sorties ASD",
                "series": _program_chart_series(asd_monthly),
                "colors": {"entrants": "green", "sortants": "red", "net": "gray"},
            },
            "fmsMatriceRisque": {
                "title": "Résultats des traitements FMS par niveau de risque",
                "rows": fms_matrix,
            },
            "menagesBloquesNational": {
                "title": "Ménages bloqués",
                "rows": blocked_national,
                "color": "red",
            },
            "fluxRegionauxAsdAmot": {
                "title": "Entrants / Sortants ASD + AMO Tadamon par région",
                "rows": combined_region_flux,
                "colors": {"entrants": "green", "sortants": "red", "net": "gray"},
            },
            "menagesBloquesRegionaux": {
                "title": "Ménages bloqués par région",
                "rows": blocked_regional,
                "color": "red",
            },
        },
        "tables": {
            "rsuEvolution": rsu_evolution,
            "asdEvolution": asd_evolution,
            "topProvincesFlux": top_flux,
            "topProvincesBloquees": top_blocked,
        },
        "footnotes": _footnotes(normalized),
        "validationSummary": validation.summary.model_dump(),
    }
    return dashboard


def linear_regression_trend(values: Sequence[int | float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [float(values[0])]
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return [float(mean_y) for _ in values]
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values, strict=True)) / denominator
    intercept = mean_y - slope * mean_x
    return [round(intercept + slope * x, 2) for x in xs]


def moving_average(values: Sequence[int | float], window: int = 3) -> list[float]:
    out: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        chunk = values[start : index + 1]
        out.append(round(sum(chunk) / len(chunk), 2))
    return out


def _metric(label: str, raw: int | float | None, *, color: str = "gray") -> dict[str, Any]:
    if raw is None:
        return {
            "label": label,
            "raw": None,
            "display": None,
            "compactDisplay": None,
            "color": color,
        }
    return {
        "label": label,
        "raw": raw,
        "display": _format_number(raw),
        "compactDisplay": _format_compact(raw),
        "color": color,
    }


def _optional_positive_metric(
    label: str,
    raw: int | float | None,
    *,
    color: str = "gray",
) -> dict[str, Any] | None:
    if raw is None or raw <= 0:
        return None
    return _metric(label, raw, color=color)


def _without_empty_metrics(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _money_metric(label: str, raw: int | float, *, color: str = "gray") -> dict[str, Any]:
    return {
        "label": label,
        "raw": raw,
        "display": _format_annual_saving(raw),
        "color": color,
    }


def _percent_metric(label: str, raw_ratio: float | None, *, color: str = "gray") -> dict[str, Any]:
    return {
        "label": label,
        "raw": raw_ratio,
        "display": _format_percent(raw_ratio),
        "color": color,
    }


def _delta_metric(label: str, delta: int | float, previous: int | float) -> dict[str, Any]:
    ratio = _ratio(delta, previous) if previous else None
    return {
        "label": label,
        "raw": delta,
        "display": _format_signed(delta),
        "percentRaw": ratio,
        "percentDisplay": _format_percent(ratio, signed=True),
        "color": "green" if delta > 0 else "red" if delta < 0 else "gray",
    }


def _current_month(metadata: dict[str, Any], normalized: dict[str, Any]) -> str:
    if metadata.get("mois_reporting_courant"):
        return str(metadata["mois_reporting_courant"])
    months = _all_flow_months(normalized)
    return months[-1] if months else ""


def _all_flow_months(normalized: dict[str, Any]) -> list[str]:
    months: set[str] = set()
    for key in (
        "rsu_new_registrations",
        "rsu_household_registrations",
        "asd_flow",
        "amo_flow",
        "asd_rescoring",
        "amo_rescoring",
        "asd_fraud",
        "amo_fraud",
        "fms_treatment",
        "fms_blocked",
    ):
        months.update(
            str(row["mois_evenement"])
            for row in normalized.get(key, [])
            if row.get("mois_evenement")
        )
    return sorted(months)


def _previous_month(current_month: str, months: list[str]) -> str:
    if current_month in months:
        index = months.index(current_month)
        if index > 0:
            return months[index - 1]
    if not current_month or len(current_month) != 7:
        return months[-1] if months else ""
    year = int(current_month[:4])
    month = int(current_month[5:])
    month -= 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def _registration_rows(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *normalized.get("rsu_new_registrations", []),
        *normalized.get("rsu_household_registrations", []),
    ]


def _registration_total(
    normalized: dict[str, Any],
    *,
    code_registre: str,
    type_unite: str,
    fallback_stock_field: str,
    reference_date: str | None,
) -> int | None:
    rows = [
        row
        for row in _registration_rows(normalized)
        if str(row.get("code_registre") or "RNP").upper() == code_registre
        and str(row.get("type_unite") or "").upper() == type_unite
    ]
    if rows:
        return sum(int(row.get("nb_nouvelles_inscriptions") or 0) for row in rows)
    return _latest_stock_value(
        normalized.get("rsu_stock", []),
        fallback_stock_field,
        reference_date,
        code_registre=code_registre,
        type_unite=type_unite,
    )


def _program_active_total(
    flow_rows: list[dict[str, Any]],
    stock_rows: list[dict[str, Any]],
    reference_date: str | None,
    *,
    type_unite: str,
) -> int | None:
    if flow_rows:
        if type_unite == "PERSONNES":
            entrants_field = "nb_entrants_personnes"
            sortants_field = "nb_sortants_personnes"
        else:
            entrants_field = "nb_entrants_menages"
            sortants_field = "nb_sortants_menages"
        return sum(
            int(row.get(entrants_field) or 0) - int(row.get(sortants_field) or 0)
            for row in flow_rows
        )
    return _latest_stock_value(
        stock_rows,
        "nb_actifs",
        reference_date,
        type_unite=type_unite,
    )


def _rsu_graph_unit(normalized: dict[str, Any]) -> str:
    metadata = normalized.get("metadata", {})
    configured = str(metadata.get("type_unite_graphique_rsu") or "PERSONNES").upper()
    flow_units = {
        str(row.get("type_unite") or "").upper()
        for row in _registration_rows(normalized)
        if row.get("mois_evenement")
        and str(row.get("code_registre") or "RNP").upper() == "RSU"
    }
    if any(
        str(row.get("code_registre") or "RNP").upper() == "RSU"
        and row.get("mois_evenement")
        and int(row.get("nb_nouvelles_personnes_rsu") or 0) > 0
        for row in _registration_rows(normalized)
    ):
        flow_units.add("PERSONNES")
    if not flow_units:
        flow_units = {
            str(row.get("type_unite") or "").upper()
            for row in _registration_rows(normalized)
            if row.get("mois_evenement")
            and str(row.get("code_registre") or "RNP").upper() == "RNP"
        }
    if configured in flow_units or not flow_units:
        return configured
    for fallback in ("PERSONNES", "MENAGES"):
        if fallback in flow_units:
            return fallback
    return sorted(flow_units)[0]


def _rsu_monthly_values(
    normalized: dict[str, Any],
    *,
    graph_unit: str | None = None,
) -> dict[str, int]:
    if graph_unit is None:
        graph_unit = _rsu_graph_unit(normalized)
    graph_unit = graph_unit.upper()
    monthly: dict[str, int] = defaultdict(int)
    has_direct_rsu_person_rows = any(
        str(row.get("code_registre") or "RNP").upper() == "RSU"
        and str(row.get("type_unite") or "").upper() == "PERSONNES"
        for row in _registration_rows(normalized)
    )
    for row in _registration_rows(normalized):
        if str(row.get("code_registre") or "RNP").upper() != "RSU":
            continue
        month = row.get("mois_evenement")
        if not month:
            continue
        if str(row.get("type_unite") or "").upper() == graph_unit:
            monthly[str(month)] += int(row.get("nb_nouvelles_inscriptions") or 0)
        elif graph_unit == "PERSONNES" and not has_direct_rsu_person_rows:
            monthly[str(month)] += int(row.get("nb_nouvelles_personnes_rsu") or 0)
    if monthly:
        return dict(sorted(monthly.items()))

    for row in _registration_rows(normalized):
        if str(row.get("code_registre") or "RNP").upper() != "RNP":
            continue
        if str(row.get("type_unite") or "").upper() != graph_unit:
            continue
        month = row.get("mois_evenement")
        if month:
            monthly[str(month)] += int(row.get("nb_nouvelles_inscriptions") or 0)
    if monthly:
        return dict(sorted(monthly.items()))

    snapshots = [
        row
        for row in normalized.get("rsu_stock", [])
        if str(row.get("code_registre") or "").upper() == "RSU"
        and str(row.get("type_unite") or "").upper() == graph_unit
        and row.get("date_reference")
    ]
    if not snapshots:
        snapshots = [
            row
            for row in normalized.get("rsu_stock", [])
            if str(row.get("code_registre") or "").upper() == "RNP"
            and str(row.get("type_unite") or "").upper() == graph_unit
            and row.get("date_reference")
        ]
    snapshots.sort(key=lambda row: row["date_reference"])
    previous: int | None = None
    for row in snapshots:
        total = int(row.get("total_cumule") or 0)
        month = str(row["date_reference"])[:7]
        if previous is not None:
            monthly[month] += max(0, total - previous)
        previous = total
    return dict(sorted(monthly.items()))


def _monthly_evolution(
    monthly: dict[str, int],
    *,
    current_month: str,
    partial_suffix: str,
    is_partial: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    previous: int | None = None
    for month, value in sorted(monthly.items()):
        delta = None if previous is None else value - previous
        ratio = None if previous is None or previous == 0 else (value - previous) / previous
        label = _format_month_label(month)
        if is_partial and month == current_month:
            label = f"{label} {partial_suffix}".strip()
        out.append(
            {
                "month": month,
                "label": label,
                "raw": value,
                "display": _format_number(value),
                "deltaRaw": delta,
                "deltaDisplay": None if delta is None else _format_signed(delta),
                "percentRaw": ratio,
                "percentDisplay": _format_percent(ratio, signed=True),
            }
        )
        previous = value
    return out


def _trend_series(monthly: dict[str, int], *, method: str) -> list[dict[str, Any]]:
    months = sorted(monthly)
    values = [monthly[month] for month in months]
    normalized = method.upper()
    if normalized == "REGRESSION_LINEAIRE":
        trend = linear_regression_trend(values)
    elif normalized == "MOYENNE_MOBILE":
        trend = moving_average(values)
    else:
        return []
    return [
        {
            "month": month,
            "raw": value,
            "display": _format_number(value),
        }
        for month, value in zip(months, trend, strict=True)
    ]


def _program_monthly(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"entrants": 0, "sortants": 0})
    for row in rows:
        month = row.get("mois_evenement")
        if not month:
            continue
        monthly[str(month)]["entrants"] += int(row.get("nb_entrants_menages") or 0)
        monthly[str(month)]["sortants"] += int(row.get("nb_sortants_menages") or 0)
    return dict(sorted(monthly.items()))


def _program_chart_series(monthly: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    return [
        {
            "month": month,
            "label": _format_month_label(month),
            "entrantsRaw": values["entrants"],
            "entrantsDisplay": _format_number(values["entrants"]),
            "sortantsRaw": values["sortants"],
            "sortantsDisplay": _format_number(values["sortants"]),
            "netRaw": values["entrants"] - values["sortants"],
            "netDisplay": _format_signed(values["entrants"] - values["sortants"]),
        }
        for month, values in sorted(monthly.items())
    ]


def _program_comparison(
    monthly: dict[str, dict[str, int]],
    current_month: str,
    previous_month: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for month in (previous_month, current_month):
        if not month:
            continue
        values = monthly.get(month, {"entrants": 0, "sortants": 0})
        net = values["entrants"] - values["sortants"]
        out.append(
            {
                "month": month,
                "label": _format_month_label(month),
                "entrantsRaw": values["entrants"],
                "entrantsDisplay": _format_number(values["entrants"]),
                "sortantsRaw": values["sortants"],
                "sortantsDisplay": _format_number(values["sortants"]),
                "netRaw": net,
                "netDisplay": _format_signed(net),
            }
        )
    return out


def _combined_region_flux(
    normalized: dict[str, Any],
    month: str | None,
    regions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"entrants": 0, "sortants": 0})
    for key in ("asd_flow", "amo_flow"):
        for row in normalized.get(key, []):
            if month is not None and row.get("mois_evenement") != month:
                continue
            code = str(row.get("code_region") or "")
            totals[code]["entrants"] += int(row.get("nb_entrants_menages") or 0)
            totals[code]["sortants"] += int(row.get("nb_sortants_menages") or 0)

    region_codes = [str(region.get("code_region")) for region in regions]
    for code in totals:
        if code not in region_codes:
            region_codes.append(code)

    return [
        _region_flux_row(code, totals.get(code, {"entrants": 0, "sortants": 0}), regions)
        for code in region_codes
    ]


def _region_flux_row(
    code_region: str,
    values: dict[str, int],
    regions: list[dict[str, Any]],
) -> dict[str, Any]:
    label = _region_label(code_region, regions)
    net = values["entrants"] - values["sortants"]
    return {
        "codeRegion": code_region,
        "region": label,
        "entrantsRaw": values["entrants"],
        "entrantsDisplay": _format_number(values["entrants"]),
        "sortantsRaw": values["sortants"],
        "sortantsDisplay": _format_number(values["sortants"]),
        "netRaw": net,
        "netDisplay": _format_signed(net),
    }


def _top_province_flux(normalized: dict[str, Any], month: str | None) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"entrants": 0, "sortants": 0})
    for key in ("asd_flow", "amo_flow"):
        for row in normalized.get(key, []):
            if month is not None and row.get("mois_evenement") != month:
                continue
            province = str(row.get("nom_province") or "")
            if not province:
                continue
            totals[province]["entrants"] += int(row.get("nb_entrants_menages") or 0)
            totals[province]["sortants"] += int(row.get("nb_sortants_menages") or 0)
    ranked = sorted(
        totals.items(),
        key=lambda item: item[1]["entrants"] - item[1]["sortants"],
        reverse=True,
    )[:5]
    return [
        {
            "province": province,
            "entrantsRaw": values["entrants"],
            "sortantsRaw": values["sortants"],
            "netRaw": values["entrants"] - values["sortants"],
            "netDisplay": _format_signed(values["entrants"] - values["sortants"]),
        }
        for province, values in ranked
    ]


def _latest_stock_value(
    rows: list[dict[str, Any]],
    value_field: str,
    reference_date: str | None,
    **filters: str,
) -> int | None:
    candidates = [
        row
        for row in rows
        if all(str(row.get(key) or "").upper() == value.upper() for key, value in filters.items())
    ]
    latest = _latest_snapshot(candidates, reference_date)
    if not latest:
        return None
    return int(latest[0].get(value_field) or 0)


def _latest_snapshot(
    rows: list[dict[str, Any]],
    reference_date: str | None,
    *,
    date_field: str = "date_reference",
) -> list[dict[str, Any]]:
    dated = [
        row
        for row in rows
        if row.get(date_field)
        and (reference_date is None or str(row[date_field]) <= str(reference_date))
    ]
    if not dated:
        return rows
    latest_date = max(str(row[date_field]) for row in dated)
    return [row for row in dated if str(row[date_field]) == latest_date]


def _fms_totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "injected": sum(int(row.get("demandes_injectees") or 0) for row in rows),
        "processed": sum(int(row.get("demandes_traitees") or 0) for row in rows),
        "confirmed": sum(int(row.get("doute_confirme") or 0) for row in rows),
        "cleared": sum(int(row.get("doute_leve") or 0) for row in rows),
    }


def _fms_matrix(
    rows: list[dict[str, Any]],
    code_labels: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"injected": 0, "processed": 0, "confirmed": 0, "cleared": 0}
    )
    for row in rows:
        key = (str(row.get("code_type_famille") or ""), str(row.get("code_niveau_risque") or ""))
        grouped[key]["injected"] += int(row.get("demandes_injectees") or 0)
        grouped[key]["processed"] += int(row.get("demandes_traitees") or 0)
        grouped[key]["confirmed"] += int(row.get("doute_confirme") or 0)
        grouped[key]["cleared"] += int(row.get("doute_leve") or 0)
    out = []
    for (family, risk), values in sorted(grouped.items()):
        out.append(
            {
                "codeTypeFamille": family,
                "typeFamille": _label(code_labels, "code_type_famille", family),
                "codeNiveauRisque": risk,
                "niveauRisque": _label(code_labels, "code_niveau_risque", risk),
                "demandesInjecteesRaw": values["injected"],
                "demandesTraiteesRaw": values["processed"],
                "douteConfirmeRaw": values["confirmed"],
                "douteConfirmePctRaw": _ratio(values["confirmed"], values["processed"]),
                "douteConfirmePctDisplay": _format_percent(
                    _ratio(values["confirmed"], values["processed"])
                ),
                "douteLeveRaw": values["cleared"],
                "douteLevePctRaw": _ratio(values["cleared"], values["processed"]),
                "douteLevePctDisplay": _format_percent(_ratio(values["cleared"], values["processed"])),
            }
        )
    return out


def _blocked_by_reason(
    rows: list[dict[str, Any]],
    code_labels: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    persons: dict[str, int] = defaultdict(int)
    for row in rows:
        reason = str(row.get("code_motif_blocage") or "")
        totals[reason] += int(row.get("nb_menages_bloques") or 0)
        persons[reason] += int(row.get("nb_personnes_bloquees") or 0)
    return [
        {
            "codeMotifBlocage": reason,
            "motifBlocage": _label(code_labels, "code_motif_blocage", reason),
            "menagesRaw": count,
            "menagesDisplay": _format_number(count),
            "personnesRaw": persons[reason],
            "personnesDisplay": _format_number(persons[reason]),
        }
        for reason, count in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def _blocked_by_region(
    rows: list[dict[str, Any]],
    regions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        totals[str(row.get("code_region") or "")] += int(row.get("nb_menages_bloques") or 0)
    ordered = [str(region.get("code_region")) for region in regions]
    for code in totals:
        if code not in ordered:
            ordered.append(code)
    return [
        {
            "codeRegion": code,
            "region": _region_label(code, regions),
            "menagesRaw": totals.get(code, 0),
            "menagesDisplay": _format_number(totals.get(code, 0)),
        }
        for code in ordered
    ]


def _top_blocked_provinces(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        province = str(row.get("nom_province") or "")
        if province:
            totals[province] += int(row.get("nb_menages_bloques") or 0)
    return [
        {
            "province": province,
            "menagesRaw": count,
            "menagesDisplay": _format_number(count),
        }
        for province, count in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    ]


def _fraud_summary(normalized: dict[str, Any], reference_date: str | None) -> dict[str, Any]:
    asd_rows = normalized.get("asd_fraud", [])
    amo_rows = normalized.get("amo_fraud", [])
    rules = normalized.get("amount_rules", [])
    asd_saving = _annual_saving(asd_rows, "ASD", "radiated_hh_count", rules, reference_date)
    amo_saving = _annual_saving(amo_rows, "AMO_TADAMON", "radiated_hh_count", rules, reference_date)
    asd_hh = sum(int(row.get("radiated_hh_count") or 0) for row in asd_rows)
    amo_hh = sum(int(row.get("radiated_hh_count") or 0) for row in amo_rows)
    asd_persons = sum(int(row.get("radiated_persons") or 0) for row in asd_rows)
    amo_persons = sum(int(row.get("radiated_persons") or 0) for row in amo_rows)
    return {
        "title": "Radiation pour fraude",
        "asdMenagesRadies": _metric("ASD - ménages radiés", asd_hh, color="red"),
        "amoMenagesRadies": _metric("AMO Tadamon - ménages radiés", amo_hh, color="red"),
        "totalMenagesRadies": _metric("Total ménages radiés", asd_hh + amo_hh, color="red"),
        "totalPersonnesRadiees": _metric("Total personnes radiées", asd_persons + amo_persons, color="red"),
        "savingAnnualRaw": asd_saving + amo_saving,
        "savingAnnualDisplay": _format_annual_saving(asd_saving + amo_saving),
        "color": "red",
    }


def _rescoring_summary(normalized: dict[str, Any], reference_date: str | None) -> dict[str, Any]:
    asd_rows = normalized.get("asd_rescoring", [])
    amo_rows = normalized.get("amo_rescoring", [])
    rules = normalized.get("amount_rules", [])
    asd_saving = _annual_saving(asd_rows, "ASD", "nb_sortants_menages", rules, reference_date)
    amo_saving = _annual_saving(amo_rows, "AMO_TADAMON", "nb_sortants_menages", rules, reference_date)
    asd_hh = sum(int(row.get("nb_sortants_menages") or 0) for row in asd_rows)
    amo_hh = sum(int(row.get("nb_sortants_menages") or 0) for row in amo_rows)
    non_comm = sum(int(row.get("nb_menages_non_communiques") or 0) for row in asd_rows + amo_rows)
    return {
        "title": "Rescoring",
        "asdMenagesSortants": _metric("ASD - ménages sortants", asd_hh, color="red"),
        "amoMenagesSortants": _metric("AMO Tadamon - ménages sortants", amo_hh, color="red"),
        "menagesNonCommuniques": _metric("Ménages non communiqués", non_comm),
        "savingAnnualRaw": asd_saving + amo_saving,
        "savingAnnualDisplay": _format_annual_saving(asd_saving + amo_saving),
    }


def _annual_saving(
    rows: list[dict[str, Any]],
    programme: str,
    count_field: str,
    rules: list[dict[str, Any]],
    reference_date: str | None,
) -> float:
    total = 0.0
    for row in rows:
        amount = row.get("montant_mensuel_arrete_dh")
        if amount is not None:
            total += float(amount) * 12
            continue
        rule = _active_amount_rule(rules, programme, reference_date)
        if rule is None:
            continue
        count = int(row.get(count_field) or 0)
        total += count * float(rule.get("montant_mensuel_dh") or 0) * float(
            rule.get("facteur_annualisation") or 12
        )
    return total


def _active_amount_rule(
    rules: list[dict[str, Any]],
    programme: str,
    reference_date: str | None,
) -> dict[str, Any] | None:
    for rule in rules:
        if str(rule.get("code_programme") or "").upper() != programme:
            continue
        start = rule.get("date_effet_debut")
        end = rule.get("date_effet_fin")
        if reference_date and start and str(start) > reference_date:
            continue
        if reference_date and end and str(end) < reference_date:
            continue
        return rule
    return None


def _footnotes(normalized: dict[str, Any]) -> list[str]:
    notes = []
    for row in normalized.get("rsu_annotations", []):
        label = row.get("libelle_annotation")
        if label:
            notes.append(str(label))
    asd_non_comm = sum(
        int(row.get("nb_menages_non_communiques") or 0)
        for row in normalized.get("asd_rescoring", [])
    )
    amo_non_comm = sum(
        int(row.get("nb_menages_non_communiques") or 0)
        for row in normalized.get("amo_rescoring", [])
    )
    if asd_non_comm > 0:
        notes.append(f"ASD: {_format_number(asd_non_comm)} ménages non communiqués par la CNRA.")
    if amo_non_comm > 0:
        notes.append(
            f"AMO Tadamon: {_format_number(amo_non_comm)} ménages non communiqués par la CNSS."
        )
    return notes


def _ordered_regions(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        normalized.get("regions", []),
        key=lambda row: (
            row.get("ordre_affichage") is None,
            row.get("ordre_affichage") or 0,
            str(row.get("nom_region") or row.get("code_region") or ""),
        ),
    )


def _region_label(code_region: str, regions: list[dict[str, Any]]) -> str:
    for region in regions:
        if str(region.get("code_region")) == str(code_region):
            return str(region.get("nom_region") or code_region)
    return code_region


def _code_labels(normalized: dict[str, Any]) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = defaultdict(dict)
    for row in normalized.get("codes", []):
        type_code = _normalize_type(row.get("type_code"))
        code = _normalize_type(row.get("code"))
        if type_code and code:
            labels[type_code][code] = str(row.get("libelle") or row.get("code"))
    return labels


def _label(
    labels: dict[str, dict[str, str]],
    type_code: str,
    code: str,
) -> str:
    type_key = _normalize_type(type_code)
    code_key = _normalize_type(code)
    aliases = [type_key]
    if type_key.startswith("code_"):
        aliases.append(type_key.removeprefix("code_"))
    for alias in aliases:
        if code_key in labels.get(alias, {}):
            return labels[alias][code_key]
    return code


def _normalize_type(value: Any) -> str:
    return str(value or "").strip().lower()


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _format_number(value: int | float) -> str:
    if isinstance(value, float) and not value.is_integer():
        raw = f"{value:,.1f}"
    else:
        raw = f"{int(round(value)):,}"
    return raw.replace(",", " ").replace(".", ",")


def _format_compact(value: int | float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{_format_decimal(value / 1_000_000)} M"
    if absolute >= 1_000:
        return f"{_format_decimal(value / 1_000)} k"
    return _format_number(value)


def _format_annual_saving(value: int | float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{_format_decimal(value / 1_000_000_000)} MM Dhs/an"
    if absolute >= 1_000_000:
        return f"{_format_decimal(value / 1_000_000)} M Dhs/an"
    if absolute >= 1_000:
        return f"{_format_decimal(value / 1_000)} k Dhs/an"
    return f"{_format_number(value)} Dhs/an"


def _format_decimal(value: int | float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _format_percent(value: float | None, *, signed: bool = False) -> str | None:
    if value is None:
        return None
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{_format_decimal(value * 100)} %"


def _format_signed(value: int | float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{_format_number(value)}"


def _format_month_label(month: str) -> str:
    if len(month) != 7:
        return month
    try:
        year = int(month[:4])
        month_number = int(month[5:])
    except ValueError:
        return month
    return f"{FR_MONTHS.get(month_number, month[5:])} {year}"
