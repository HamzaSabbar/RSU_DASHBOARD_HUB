from __future__ import annotations

import io

import pandas as pd

from boards.macro_national.schemas import FileKind

FRENCH_MONTHS = {
    "janv": 1, "jan": 1, "janvier": 1, "january": 1,
    "févr": 2, "fev": 2, "fevr": 2, "février": 2, "fevrier": 2, "feb": 2, "february": 2,
    "mars": 3, "mar": 3, "march": 3,
    "avr": 4, "avril": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "june": 6,
    "juil": 7, "juillet": 7, "jul": 7, "july": 7,
    "août": 8, "aout": 8, "aoû": 8, "aug": 8, "august": 8,
    "sept": 9, "sep": 9, "septembre": 9, "september": 9,
    "oct": 10, "octobre": 10, "october": 10,
    "nov": 11, "novembre": 11, "november": 11,
    "déc": 12, "dec": 12, "décembre": 12, "decembre": 12, "december": 12,
}


def _month_token_to_int(token: str) -> int | None:
    t = token.strip().lower().rstrip(".")
    if t in FRENCH_MONTHS:
        return FRENCH_MONTHS[t]
    if t.isdigit():
        n = int(t)
        if 1 <= n <= 12:
            return n
    return None


def parse_inscriptions_rnp(content: bytes) -> pd.DataFrame:
    """Return a tidy DataFrame with columns: province, month (YYYY-MM), value."""
    buffer = io.BytesIO(content)
    raw = pd.read_excel(buffer, header=None, sheet_name=0, engine="openpyxl")
    if raw.empty or raw.shape[1] < 2:
        raise ValueError("feuille vide ou colonnes manquantes")

    row0 = raw.iloc[0].tolist()
    row1 = raw.iloc[1].tolist()
    province_col = 0

    header_map: dict[int, str] = {}
    current_year: int | None = None
    for col_idx in range(1, raw.shape[1]):
        y = row0[col_idx]
        m = row1[col_idx]
        if isinstance(y, (int, float)) and not pd.isna(y):
            current_year = int(y)
        elif isinstance(y, str) and y.strip().isdigit():
            current_year = int(y.strip())

        month_token = str(m).strip() if m is not None and not pd.isna(m) else ""
        month_num = _month_token_to_int(month_token) if month_token else None

        if current_year and month_num:
            header_map[col_idx] = f"{current_year:04d}-{month_num:02d}"
        elif month_token.lower() in {"total", "totaux"}:
            header_map[col_idx] = "TOTAL"

    data_rows: list[dict[str, object]] = []
    for row_idx in range(2, raw.shape[0]):
        province = raw.iat[row_idx, province_col]
        if pd.isna(province):
            continue
        province_str = str(province).strip()
        if not province_str or province_str.lower() in {"total", "totaux"}:
            continue
        for col_idx, month_label in header_map.items():
            if month_label == "TOTAL":
                continue
            cell = raw.iat[row_idx, col_idx]
            if pd.isna(cell):
                continue
            try:
                value = int(float(cell))
            except (TypeError, ValueError):
                continue
            data_rows.append(
                {"province": province_str, "month": month_label, "value": value}
            )

    if not data_rows:
        raise ValueError("aucune donnée mensuelle détectée")
    return pd.DataFrame(data_rows)


def _read_single_sheet(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), sheet_name=0, engine="openpyxl")


def parse_traitement_fms(content: bytes) -> pd.DataFrame:
    df = _read_single_sheet(content)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    required = {"type_famille", "niveau_risque", "doute_confirme", "doute_leve"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"colonnes manquantes: {sorted(missing)}")
    df["type_famille"] = df["type_famille"].astype(str).str.strip()
    df["niveau_risque"] = df["niveau_risque"].astype(str).str.strip()
    df["doute_confirme"] = pd.to_numeric(df["doute_confirme"], errors="coerce").fillna(0).astype(int)
    df["doute_leve"] = pd.to_numeric(df["doute_leve"], errors="coerce").fillna(0).astype(int)
    return df[["type_famille", "niveau_risque", "doute_confirme", "doute_leve"]]


def parse_flux_regions(content: bytes) -> pd.DataFrame:
    df = _read_single_sheet(content)
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"region", "entrants", "sortants"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"colonnes manquantes: {sorted(missing)}")
    df["region"] = df["region"].astype(str).str.strip()
    df["entrants"] = pd.to_numeric(df["entrants"], errors="coerce").fillna(0).astype(int)
    df["sortants"] = pd.to_numeric(df["sortants"], errors="coerce").fillna(0).astype(int)
    return df[["region", "entrants", "sortants"]]


def parse_menages_bloques_regions(content: bytes) -> pd.DataFrame:
    df = _read_single_sheet(content)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    if "region" not in df.columns or "bloques" not in df.columns:
        raise ValueError("colonnes manquantes: region, bloques")
    df["region"] = df["region"].astype(str).str.strip()
    df["bloques"] = pd.to_numeric(df["bloques"], errors="coerce").fillna(0).astype(int)
    for c in ("fms_fraude", "multi_noyau_procedure", "individuel_procedure"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        else:
            df[c] = 0
    return df[["region", "bloques", "fms_fraude", "multi_noyau_procedure", "individuel_procedure"]]


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
    """Sniff the first sheet for known markers."""
    name = filename.lower()
    if "inscrits" in name or "inscription" in name or "rnp" in name:
        return FileKind.INSCRIPTIONS_RNP
    if "fms" in name or "traitement" in name:
        return FileKind.TRAITEMENT_FMS
    if "flux" in name or "asd" in name:
        return FileKind.FLUX_REGIONS
    if "bloqu" in name:
        return FileKind.MENAGES_BLOQUES_REGIONS
    if "econom" in name or "budget" in name:
        return FileKind.ECONOMIE_BUDGETAIRE

    try:
        df = pd.read_excel(io.BytesIO(content), header=None, nrows=2, engine="openpyxl")
        header_text = " ".join(str(v) for v in df.iloc[:2].fillna("").values.flatten()).lower()
    except Exception:
        return None
    if "province" in header_text:
        return FileKind.INSCRIPTIONS_RNP
    return None
