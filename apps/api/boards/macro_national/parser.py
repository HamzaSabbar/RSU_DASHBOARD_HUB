from __future__ import annotations

import io

import pandas as pd

from boards.macro_national.schemas import FileKind

_CONSOLIDATED_COLS = {
    "month",
    "region",
    "province",
    "inscriptions_rsu_individus",
    "entrants_menage_asd",
    "sortants_menage_asd",
    "entrants_menage_amot",
    "sortants_menage_amot",
    "bloque_fms",
    "bloque_multi",
    "bloque_individuel",
}

_CONSOLIDATED_INT_COLS = [
    "inscriptions_rsu_individus",
    "entrants_menage_asd",
    "sortants_menage_asd",
    "entrants_menage_amot",
    "sortants_menage_amot",
    "bloque_fms",
    "bloque_multi",
    "bloque_individuel",
]


def parse_consolidated(content: bytes) -> pd.DataFrame:
    """Parse the consolidated flat file.

    Expected columns (case-insensitive, spaces→underscores):
    month, region, province, inscriptions_rsu_individus,
    entrants_menage_asd, sortants_menage_asd, entrants_menage_amot,
    sortants_menage_amot, bloque_fms, bloque_multi, bloque_individuel.
    """
    df = pd.read_excel(io.BytesIO(content), sheet_name=0, engine="openpyxl")
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    missing = _CONSOLIDATED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"colonnes manquantes : {sorted(missing)}")

    df["month"] = df["month"].astype(str).str.strip()
    df["region"] = df["region"].astype(str).str.strip()
    df["province"] = df["province"].astype(str).str.strip()
    for col in _CONSOLIDATED_INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    ordered = ["month", "region", "province"] + _CONSOLIDATED_INT_COLS
    return df[ordered].reset_index(drop=True)


def _read_single_sheet(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), sheet_name=0, engine="openpyxl")


def parse_economie_budgetaire(content: bytes) -> dict[str, int]:
    df = _read_single_sheet(content)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if {"fraude", "rescoring", "total"}.issubset(df.columns) and not df.empty:
        row = df.iloc[0]
        return {
            "fraude": int(float(row["fraude"])),
            "rescoring": int(float(row["rescoring"])),
            "total": int(float(row["total"])),
        }
    raise ValueError("schéma attendu: colonnes fraude, rescoring, total sur une ligne")


def detect_file_kind(filename: str, content: bytes) -> FileKind | None:
    name = filename.lower()
    if "econom" in name or "budget" in name:
        return FileKind.ECONOMIE_BUDGETAIRE

    try:
        df = pd.read_excel(io.BytesIO(content), nrows=1, engine="openpyxl")
        cols = {str(c).strip().lower().replace(" ", "_") for c in df.columns}
    except Exception:
        return None

    if "inscriptions_rsu_individus" in cols:
        return FileKind.CONSOLIDATED
    if {"fraude", "rescoring", "total"}.issubset(cols):
        return FileKind.ECONOMIE_BUDGETAIRE
    return None
