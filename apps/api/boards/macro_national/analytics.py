from __future__ import annotations

import pandas as pd

from boards.macro_national.schemas import (
    EconomieBudgetaire,
    FMSBucket,
    FMSKPIs,
    InscriptionsKPIs,
    MenagesBloquesCategory,
    MonthlyPoint,
    ProvinceRanking,
    RegionBloques,
    RegionFlux,
)


def compute_inscriptions_kpis(df: pd.DataFrame, personnes_per_menage: float = 3.3) -> InscriptionsKPIs:
    """df columns: province, month, value (count of new ménages in that month)."""
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


def compute_fms_kpis(df: pd.DataFrame) -> FMSKPIs:
    if df.empty:
        return FMSKPIs(demandes_traitees=0, doute_confirme=0, doute_leve=0)
    confirme = int(df["doute_confirme"].sum())
    leve = int(df["doute_leve"].sum())
    return FMSKPIs(
        demandes_traitees=confirme + leve,
        doute_confirme=confirme,
        doute_leve=leve,
    )


def compute_fms_buckets(df: pd.DataFrame) -> list[FMSBucket]:
    return [
        FMSBucket(
            type_famille=str(row["type_famille"]),
            niveau_risque=str(row["niveau_risque"]),
            doute_confirme=int(row["doute_confirme"]),
            doute_leve=int(row["doute_leve"]),
        )
        for _, row in df.iterrows()
    ]


def compute_region_flux(df: pd.DataFrame) -> list[RegionFlux]:
    return [
        RegionFlux(
            region=str(row["region"]),
            entrants=int(row["entrants"]),
            sortants=int(row["sortants"]),
        )
        for _, row in df.iterrows()
    ]


def compute_menages_bloques_categories(df: pd.DataFrame) -> list[MenagesBloquesCategory]:
    if df.empty:
        return []
    return [
        MenagesBloquesCategory(category="FMS fraude", count=int(df["fms_fraude"].sum())),
        MenagesBloquesCategory(
            category="Multi-noyau procédure",
            count=int(df["multi_noyau_procedure"].sum()),
        ),
        MenagesBloquesCategory(
            category="Individuel procédure",
            count=int(df["individuel_procedure"].sum()),
        ),
    ]


def compute_region_bloques(df: pd.DataFrame) -> list[RegionBloques]:
    return [
        RegionBloques(region=str(row["region"]), bloques=int(row["bloques"]))
        for _, row in df.iterrows()
    ]


def compute_top_bloques_regions(df: pd.DataFrame, k: int = 5) -> list[ProvinceRanking]:
    if df.empty:
        return []
    top = df.sort_values("bloques", ascending=False).head(k)
    return [
        ProvinceRanking(province=str(row["region"]), value=int(row["bloques"]))
        for _, row in top.iterrows()
    ]


def compute_economie_budgetaire(values: dict[str, int]) -> EconomieBudgetaire:
    return EconomieBudgetaire(
        fraude=int(values.get("fraude", 0)),
        rescoring=int(values.get("rescoring", 0)),
        total=int(values.get("total", 0)),
    )


def compute_top_provinces(df: pd.DataFrame, k: int = 5) -> list[ProvinceRanking]:
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
