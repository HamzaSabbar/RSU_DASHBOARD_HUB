from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class FileKind(str, Enum):
    CONSOLIDATED = "consolidated"
    ECONOMIE_BUDGETAIRE = "economie_budgetaire"


class ExpectedFile(BaseModel):
    kind: FileKind
    label: str
    description: str
    required_columns: list[str]


EXPECTED_FILES: list[ExpectedFile] = [
    ExpectedFile(
        kind=FileKind.CONSOLIDATED,
        label="Données consolidées",
        description=(
            "Fichier principal : une ligne par mois × province. "
            "Colonnes requises : month (YYYY-MM), region, province, "
            "inscriptions_rsu_individus, entrants_menage_asd, sortants_menage_asd, "
            "entrants_menage_amot, sortants_menage_amot, bloque_fms, bloque_multi, "
            "bloque_individuel."
        ),
        required_columns=[
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
        ],
    ),
    ExpectedFile(
        kind=FileKind.ECONOMIE_BUDGETAIRE,
        label="Économie budgétaire",
        description="Scalars fraude / rescoring / total optimisation.",
        required_columns=["fraude", "rescoring", "total"],
    ),
]


class InscriptionsKPIs(BaseModel):
    total_menages: int
    total_personnes: int
    new_menages_last_month: int
    new_menages_last_month_pct_change: float | None


class ProgrammesSociaux(BaseModel):
    tadamon_beneficiaries: int
    amo_beneficiaries: int


class MonthlyPoint(BaseModel):
    month: str  # "YYYY-MM"
    value: int
    delta: int | None = None
    pct_change: float | None = None


class EntriesExitsPoint(BaseModel):
    month: str
    entrants: int
    sortants: int


class FMSKPIs(BaseModel):
    demandes_traitees: int
    doute_confirme: int
    doute_leve: int


class FMSBucket(BaseModel):
    type_famille: str
    niveau_risque: str
    doute_confirme: int
    doute_leve: int


class RadiationFraude(BaseModel):
    menages_radies: int
    personnes_radiees: int


class Rescoring(BaseModel):
    menages_rescores: int
    personnes_rescorees: int


class EconomieBudgetaire(BaseModel):
    fraude: int
    rescoring: int
    total: int


class MenagesBloquesCategory(BaseModel):
    category: str
    count: int


class RegionFlux(BaseModel):
    region: str
    entrants: int
    sortants: int


class RegionBloques(BaseModel):
    region: str
    bloques: int


class ProvinceRanking(BaseModel):
    province: str
    value: int


class MacroNationalPayload(BaseModel):
    reporting_date: str | None = None
    inscriptions_kpis: InscriptionsKPIs | None = None
    programmes_sociaux: ProgrammesSociaux | None = None
    monthly_evolution: list[MonthlyPoint] | None = None
    entries_exits: list[EntriesExitsPoint] | None = None
    fms_kpis: FMSKPIs | None = None
    fms_buckets: list[FMSBucket] | None = None
    radiation_fraude: RadiationFraude | None = None
    rescoring: Rescoring | None = None
    economie_budgetaire: EconomieBudgetaire | None = None
    menages_bloques_categories: list[MenagesBloquesCategory] | None = None
    region_flux: list[RegionFlux] | None = None
    region_bloques: list[RegionBloques] | None = None
    top_provinces_inscriptions: list[ProvinceRanking] | None = None
    top_provinces_bloques: list[ProvinceRanking] | None = None


EMPTY_PAYLOAD = MacroNationalPayload()
