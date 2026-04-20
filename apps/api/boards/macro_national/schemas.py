from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class FileKind(str, Enum):
    INSCRIPTIONS_RNP = "inscriptions_rnp"
    TRAITEMENT_FMS = "traitement_fms"
    FLUX_REGIONS = "flux_regions"
    MENAGES_BLOQUES_REGIONS = "menages_bloques_regions"
    ECONOMIE_BUDGETAIRE = "economie_budgetaire"


class ExpectedFile(BaseModel):
    kind: FileKind
    label: str
    description: str
    required_columns: list[str]


EXPECTED_FILES: list[ExpectedFile] = [
    ExpectedFile(
        kind=FileKind.INSCRIPTIONS_RNP,
        label="Inscriptions RNP",
        description=(
            "Stat des nouveaux inscrits RNP. Province en colonne A, "
            "colonnes mensuelles YYYY-MM, colonne Total en fin."
        ),
        required_columns=["Province"],
    ),
    ExpectedFile(
        kind=FileKind.TRAITEMENT_FMS,
        label="Traitement FMS",
        description=(
            "Résultats FMS: type de famille x niveau de risque x "
            "doute confirmé / doute levé."
        ),
        required_columns=["type_famille", "niveau_risque", "doute_confirme", "doute_leve"],
    ),
    ExpectedFile(
        kind=FileKind.FLUX_REGIONS,
        label="Flux ASD par région",
        description="Entrants / sortants ASD + AMO Tadamon par région.",
        required_columns=["region", "entrants", "sortants"],
    ),
    ExpectedFile(
        kind=FileKind.MENAGES_BLOQUES_REGIONS,
        label="Ménages bloqués par région",
        description="Ménages bloqués par région.",
        required_columns=["region", "bloques"],
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
    type_famille: str  # "Individuels" | "Mariés avec enfants" | "Mono-parental" | "Multi-noyaux"
    niveau_risque: str  # "Élevé" | "Moyen"
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
    category: str  # "FMS fraude" | "Multi-noyau procédure" | "Individuel procédure"
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
