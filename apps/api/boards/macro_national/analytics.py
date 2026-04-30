from __future__ import annotations

import pandas as pd

from boards.macro_national.schemas import (
    EconomieBudgetaire,
    EntriesExitsPoint,
    InscriptionsKPIs,
    MenagesBloquesCategory,
    MonthlyPoint,
    ProvinceRanking,
    RegionBloques,
    RegionFlux,
)


def compute_inscriptions_kpis(df: pd.DataFrame, personnes_per_menage: float = 3.3) -> InscriptionsKPIs:
    """df columns: province, month, value (aggregated inscriptions per province-month)."""
    if df.empty:
        return InscriptionsKPIs(
            total_menages=0,
            total_personnes=0,
            new_menages_last_month=0,
            new_menages_last_month_pct_change=None,
        )

    total = int(df["value"].sum())
    monthly = (
        df.groupby("month", as_index=False)["value"]
        .sum()
        .sort_values("month", ascending=True)
        .reset_index(drop=True)
    )
    last = int(monthly["value"].iloc[-1])
    pct: float | None = None
    if len(monthly) >= 2:
        prev = int(monthly["value"].iloc[-2])
        if prev > 0:
            pct = round(((last - prev) / prev) * 100.0, 2)

    return InscriptionsKPIs(
        total_menages=total,
        total_personnes=int(round(total * personnes_per_menage)),
        new_menages_last_month=last,
        new_menages_last_month_pct_change=pct,
    )


def compute_monthly_evolution(df: pd.DataFrame) -> list[MonthlyPoint]:
    """df columns: province, month, value."""
    if df.empty:
        return []
    monthly = (
        df.groupby("month", as_index=False)["value"]
        .sum()
        .sort_values("month", ascending=True)
        .reset_index(drop=True)
    )
    points: list[MonthlyPoint] = []
    prev_value: int | None = None
    for _, row in monthly.iterrows():
        value = int(row["value"])
        delta = None if prev_value is None else value - prev_value
        pct = None
        if prev_value is not None and prev_value > 0:
            pct = round(((value - prev_value) / prev_value) * 100.0, 2)
        points.append(
            MonthlyPoint(month=str(row["month"]), value=value, delta=delta, pct_change=pct)
        )
        prev_value = value
    return points


def compute_top_provinces(df: pd.DataFrame, k: int = 5) -> list[ProvinceRanking]:
    """df columns: province, month, value."""
    if df.empty:
        return []
    totals = (
        df.groupby("province", as_index=False)["value"]
        .sum()
        .sort_values("value", ascending=False)
        .head(k)
    )
    return [
        ProvinceRanking(province=str(row["province"]), value=int(row["value"]))
        for _, row in totals.iterrows()
    ]


def compute_entries_exits(df: pd.DataFrame) -> list[EntriesExitsPoint]:
    """df is the consolidated dataframe. Sums asd + amot entrants/sortants per month."""
    tmp = df.copy()
    tmp["entrants"] = tmp["entrants_menage_asd"] + tmp["entrants_menage_amot"]
    tmp["sortants"] = tmp["sortants_menage_asd"] + tmp["sortants_menage_amot"]
    by_month = (
        tmp.groupby("month", as_index=False)[["entrants", "sortants"]]
        .sum()
        .sort_values("month")
    )
    return [
        EntriesExitsPoint(
            month=str(row["month"]),
            entrants=int(row["entrants"]),
            sortants=int(row["sortants"]),
        )
        for _, row in by_month.iterrows()
    ]


def compute_region_flux(df: pd.DataFrame) -> list[RegionFlux]:
    """df is the consolidated dataframe. Aggregates entrants/sortants by region."""
    tmp = df.copy()
    tmp["entrants"] = tmp["entrants_menage_asd"] + tmp["entrants_menage_amot"]
    tmp["sortants"] = tmp["sortants_menage_asd"] + tmp["sortants_menage_amot"]
    by_region = (
        tmp.groupby("region", as_index=False)[["entrants", "sortants"]]
        .sum()
        .sort_values("region")
    )
    return [
        RegionFlux(
            region=str(row["region"]),
            entrants=int(row["entrants"]),
            sortants=int(row["sortants"]),
        )
        for _, row in by_region.iterrows()
    ]


def compute_menages_bloques_categories(df: pd.DataFrame) -> list[MenagesBloquesCategory]:
    """df is the consolidated dataframe."""
    if df.empty:
        return []
    return [
        MenagesBloquesCategory(category="FMS fraude", count=int(df["bloque_fms"].sum())),
        MenagesBloquesCategory(
            category="Multi-noyau procédure",
            count=int(df["bloque_multi"].sum()),
        ),
        MenagesBloquesCategory(
            category="Individuel procédure",
            count=int(df["bloque_individuel"].sum()),
        ),
    ]


def compute_region_bloques(df: pd.DataFrame) -> list[RegionBloques]:
    """df is the consolidated dataframe. Sums all blocked categories per region."""
    tmp = df.copy()
    tmp["total_bloques"] = tmp["bloque_fms"] + tmp["bloque_multi"] + tmp["bloque_individuel"]
    by_region = (
        tmp.groupby("region", as_index=False)["total_bloques"]
        .sum()
        .sort_values("region")
    )
    return [
        RegionBloques(region=str(row["region"]), bloques=int(row["total_bloques"]))
        for _, row in by_region.iterrows()
    ]


def compute_top_bloques_regions(df: pd.DataFrame, k: int = 5) -> list[ProvinceRanking]:
    """Top provinces by total blocked households. df is the consolidated dataframe."""
    if df.empty:
        return []
    tmp = df.copy()
    tmp["total_bloques"] = tmp["bloque_fms"] + tmp["bloque_multi"] + tmp["bloque_individuel"]
    by_province = (
        tmp.groupby("province", as_index=False)["total_bloques"]
        .sum()
        .sort_values("total_bloques", ascending=False)
        .head(k)
    )
    return [
        ProvinceRanking(province=str(row["province"]), value=int(row["total_bloques"]))
        for _, row in by_province.iterrows()
    ]


def compute_economie_budgetaire(values: dict[str, int]) -> EconomieBudgetaire:
    return EconomieBudgetaire(
        fraude=int(values.get("fraude", 0)),
        rescoring=int(values.get("rescoring", 0)),
        total=int(values.get("total", 0)),
    )
