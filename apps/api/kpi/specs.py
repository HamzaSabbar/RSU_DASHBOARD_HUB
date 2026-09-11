"""The 18 KPI specs — the single source of truth for parsing, validation,
storage and analytics of every RSU process KPI sheet.

Column `source_name` strings are copied verbatim from the seed workbook
(`data/imports/seed/Donnees_synthetiques_kpi_VF.xlsx`), including
its exact Unicode punctuation (curly apostrophes, ≤/≥, guillemets). Every
sheet's real data starts at row 6: rows 1-3 are title/note/formula, row 4 is
blank, row 5 is the header row — `header_row=4` (0-based) throughout, per
`docs/DATA_CONTRACT.md`.

`supported_filters` and `supported_breakdowns` are declared independently per
KPI (never inferred from one another): a filter restricts which rows are
summed, a breakdown groups the already-filtered rows. Most KPIs can filter
and break down on the same dimensions, but the two lists are still spelled
out separately here on purpose -- INS-03 is the one KPI where a breakdown
(`controlled_field`, `incoherence_type`) reads a different physical table
than its filters do, which only an explicit, per-breakdown declaration can
express.
"""

from __future__ import annotations

from kpi import models as m
from kpi import validation as v
from kpi.registry import (
    AggregationStrategy,
    BreakdownSpec,
    ColumnSpec,
    KpiSpec,
    SheetTableSpec,
    register,
)

# ---------------------------------------------------------------------------
# Accès
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="ACC-01",
        section="acces",
        title="Taux de conversion de l'enrôlement RNP vers la présence au RSU",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset({"period", "region", "province", "milieu", "age_band"}),
        supported_breakdowns=(
            BreakdownSpec("age_band"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="age_band",
        measures=("30j", "90j"),
        ratio_windows=(("30j", "present_rsu_30j"), ("90j", "present_rsu_90j")),
        denominator_field="rnp_idcs_actif",
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="ACC-01",
                header_row=4,
                usecols="A:H",
                model=m.KpiAcc01,
                natural_key=("period", "region", "province", "milieu", "age_band"),
                columns=(
                    ColumnSpec("Mois d’enrôlement RNP", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Tranche d’âge", "age_band"),
                    ColumnSpec("Effectif RNP avec IDCS actif", "rnp_idcs_actif", "int"),
                    ColumnSpec("Effectif présent au RSU ≤30j", "present_rsu_30j", "int"),
                    ColumnSpec("Effectif présent au RSU ≤90j", "present_rsu_90j", "int"),
                ),
                validators=(
                    v.RequiredColumns(
                        ("period", "region", "province", "milieu", "age_band")
                    ),
                    v.NonNegative(("rnp_idcs_actif", "present_rsu_30j", "present_rsu_90j")),
                    v.Ordering(("present_rsu_30j", "present_rsu_90j", "rnp_idcs_actif")),
                    v.UniqueKey(("period", "region", "province", "milieu", "age_band")),
                ),
            ),
        ),
    )
)

# ---------------------------------------------------------------------------
# Inscription
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="INS-01",
        section="inscription",
        title="Taux d'aboutissement du parcours d'inscription à 30, 60 et 90 jours",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset({"period", "region", "province", "milieu", "channel"}),
        supported_breakdowns=(
            BreakdownSpec("channel"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="channel",
        measures=("30j", "60j", "90j"),
        ratio_windows=(
            ("30j", "finalisees_30j"),
            ("60j", "finalisees_60j"),
            ("90j", "finalisees_90j"),
        ),
        denominator_field="demandes_initiees",
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="INS-01",
                header_row=4,
                usecols="A:I",
                model=m.KpiIns01,
                natural_key=("period", "region", "province", "milieu", "channel"),
                columns=(
                    ColumnSpec("Mois_creation", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Canal", "channel"),
                    ColumnSpec("Effectif_demandes_initiees", "demandes_initiees", "int"),
                    ColumnSpec("Finalisees_≤30j", "finalisees_30j", "int"),
                    ColumnSpec("Finalisees_≤60j", "finalisees_60j", "int"),
                    ColumnSpec("Finalisees_≤90j", "finalisees_90j", "int"),
                ),
                validators=(
                    v.NonNegative(
                        ("demandes_initiees", "finalisees_30j", "finalisees_60j", "finalisees_90j")
                    ),
                    v.Ordering(
                        ("finalisees_30j", "finalisees_60j", "finalisees_90j", "demandes_initiees")
                    ),
                    v.UniqueKey(("period", "region", "province", "milieu", "channel")),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="INS-02",
        section="inscription",
        title="Délai de bout en bout de l'inscription RSU",
        unit="jours",
        aggregation_strategy=AggregationStrategy.PERCENTILE,
        supported_filters=frozenset({"period", "region", "province", "milieu", "channel"}),
        supported_breakdowns=(
            BreakdownSpec("channel"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="channel",
        measures=("median", "p75", "p90"),
        percentile_table_index=1,
        percentile_fields=("mediane_nationale", "p75_national", "p90_national"),
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="INS-02",
                header_row=4,
                usecols="A:I",
                model=m.KpiIns02,
                natural_key=("period", "region", "province", "milieu", "channel"),
                columns=(
                    ColumnSpec("Mois_de_dépôt", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Canal", "channel"),
                    ColumnSpec("Nombre de dossiers finalisés", "dossiers_finalises", "int"),
                    ColumnSpec("Délai médian", "mediane_jours", "float", nullable=True),
                    ColumnSpec("P75", "p75_jours", "float", nullable=True),
                    ColumnSpec("P90", "p90_jours", "float", nullable=True),
                ),
                validators=(
                    v.NonNegative(("dossiers_finalises",)),
                    v.Ordering(("mediane_jours", "p75_jours", "p90_jours")),
                    v.UniqueKey(("period", "region", "province", "milieu", "channel")),
                ),
            ),
            SheetTableSpec(
                table_key="national",
                sheet_name="INS-02",
                header_row=4,
                usecols="K:N",
                model=m.KpiIns02National,
                natural_key=("period",),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec("Médiane nationale", "mediane_nationale", "float", nullable=True),
                    ColumnSpec("P75 national", "p75_national", "float", nullable=True),
                    ColumnSpec("P90 national", "p90_national", "float", nullable=True),
                ),
                validators=(
                    v.Ordering(("mediane_nationale", "p75_national", "p90_national")),
                    v.UniqueKey(("period",)),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="INS-03",
        section="inscription",
        title="Taux d'incohérence des données entre le RNP et le RSU",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset(
            {"period", "region", "province", "milieu", "controlled_field", "incoherence_type"}
        ),
        # controlled_field/incoherence_type live only on the field-analysis table
        # (H:O) with their own numerator column -- they cannot be read off the
        # main A:F table, so each gets an explicit table_key + numerator override.
        supported_breakdowns=(
            BreakdownSpec("controlled_field", table_key="field", numerator_field="nb_incoherents"),
            BreakdownSpec("incoherence_type", table_key="field", numerator_field="nb_incoherents"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="controlled_field",
        period_grain="quarter",
        measures=("value",),
        ratio_windows=(("value", "personnes_avec_incoherence"),),
        denominator_field="personnes_comparees",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="INS-03",
                header_row=4,
                usecols="A:F",
                model=m.KpiIns03,
                natural_key=("period", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Trimestre", "period", "quarter"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de personnes avec ≥1 incohérence",
                        "personnes_avec_incoherence",
                        "int",
                    ),
                    ColumnSpec(
                        "Nombre total de personnes comparées", "personnes_comparees", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("personnes_avec_incoherence", "personnes_comparees")),
                    v.NumeratorLessEqualDenominator(
                        "personnes_avec_incoherence", "personnes_comparees"
                    ),
                    v.UniqueKey(("period", "region", "province", "milieu")),
                ),
            ),
            SheetTableSpec(
                table_key="field",
                sheet_name="INS-03",
                header_row=4,
                usecols="H:O",
                model=m.KpiIns03Field,
                natural_key=(
                    "period",
                    "region",
                    "province",
                    "milieu",
                    "controlled_field",
                    "incoherence_type",
                ),
                columns=(
                    # pandas suffixes these with ".1" because the same header text
                    # already appears once in the A:F global table on this sheet.
                    ColumnSpec("Trimestre.1", "period", "quarter"),
                    ColumnSpec("Région.1", "region"),
                    ColumnSpec("Province / Préfecture.1", "province"),
                    ColumnSpec("Milieu.1", "milieu"),
                    ColumnSpec("Champ contrôlé", "controlled_field"),
                    ColumnSpec("Type d’incohérence", "incoherence_type"),
                    ColumnSpec(
                        "Nombre de personnes avec ≥1 incohérence.1", "nb_incoherents", "int"
                    ),
                    ColumnSpec(
                        "Nombre total de personnes comparées.1", "personnes_comparees", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("nb_incoherents", "personnes_comparees")),
                    v.NumeratorLessEqualDenominator("nb_incoherents", "personnes_comparees"),
                    v.UniqueKey(
                        (
                            "period",
                            "region",
                            "province",
                            "milieu",
                            "controlled_field",
                            "incoherence_type",
                        )
                    ),
                ),
            ),
        ),
    )
)

# ---------------------------------------------------------------------------
# Fiabilisation des sources
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="FSC-01",
        section="fiabilisation-sources",
        title="Délai de réponse utilisable par source administrative",
        unit="jours",
        aggregation_strategy=AggregationStrategy.WEIGHTED_MEAN,
        supported_filters=frozenset({"period", "administrative_source", "flow_type"}),
        supported_breakdowns=(
            BreakdownSpec("administrative_source"),
            BreakdownSpec("flow_type"),
        ),
        default_breakdown="administrative_source",
        measures=("value",),
        weight_field="requetes_valides",
        value_field="delai_moyen_jours",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="FSC-01",
                header_row=4,
                usecols="A:G",
                model=m.KpiFsc01,
                natural_key=("period", "administrative_source", "flow_type"),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec("Source administrative", "administrative_source"),
                    ColumnSpec("Type de flux", "flow_type"),
                    ColumnSpec(
                        "Nombre de requêtes valides envoyées", "requetes_valides", "int"
                    ),
                    ColumnSpec("Délai moyen", "delai_moyen_jours", "float", nullable=True),
                    ColumnSpec(
                        "Délai médian", "delai_median_jours", "float", nullable=True
                    ),
                    ColumnSpec("P90 du délai", "p90_jours", "float", nullable=True),
                ),
                validators=(
                    v.NonNegative(("requetes_valides",)),
                    v.Ordering(("delai_median_jours", "p90_jours")),
                    v.UniqueKey(("period", "administrative_source", "flow_type")),
                ),
            ),
        ),
    )
)

# ---------------------------------------------------------------------------
# Mise à jour & rescoring
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="MAJ-01",
        section="maj-rescoring",
        title="Délai bout-en-bout mise à jour → nouvel ISE",
        unit="jours",
        aggregation_strategy=AggregationStrategy.PERCENTILE,
        supported_filters=frozenset(
            {
                "period",
                "region",
                "province",
                "milieu",
                "channel",
                "update_type",
                "complexity",
            }
        ),
        supported_breakdowns=(
            BreakdownSpec("update_type"),
            BreakdownSpec("complexity"),
            BreakdownSpec("channel"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="update_type",
        measures=("median", "p75", "p90"),
        percentile_table_index=1,
        percentile_fields=("mediane_delai_national", "p75_national", "p90_national"),
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="MAJ-01",
                header_row=4,
                usecols="A:L",
                model=m.KpiMaj01,
                natural_key=(
                    "period",
                    "update_type",
                    "complexity",
                    "region",
                    "province",
                    "milieu",
                    "channel",
                ),
                columns=(
                    ColumnSpec("Mois d’initiation", "period", "date"),
                    ColumnSpec("Type de mise à jour", "update_type"),
                    ColumnSpec("Standard / non standard", "complexity"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Canal", "channel"),
                    ColumnSpec("Nombre de MAJ finalisées", "maj_finalisees", "int"),
                    ColumnSpec("Délai médian", "mediane_jours", "float", nullable=True),
                    ColumnSpec("P75", "p75_jours", "float", nullable=True),
                    ColumnSpec("P90", "p90_jours", "float", nullable=True),
                    ColumnSpec(
                        "Nombre total de dossiers concernés", "dossiers_concernes", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("maj_finalisees", "dossiers_concernes")),
                    v.NumeratorLessEqualDenominator("maj_finalisees", "dossiers_concernes"),
                    v.Ordering(("mediane_jours", "p75_jours", "p90_jours")),
                    v.ConditionalNull("maj_finalisees", 0, "mediane_jours"),
                    v.ConditionalNull("maj_finalisees", 0, "p75_jours"),
                    v.ConditionalNull("maj_finalisees", 0, "p90_jours"),
                    v.UniqueKey(
                        (
                            "period",
                            "update_type",
                            "complexity",
                            "region",
                            "province",
                            "milieu",
                            "channel",
                        )
                    ),
                ),
            ),
            SheetTableSpec(
                table_key="national",
                sheet_name="MAJ-01",
                header_row=4,
                usecols="N:Q",
                model=m.KpiMaj01National,
                natural_key=("period",),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec(
                        "Délai médian national",
                        "mediane_delai_national",
                        "float",
                        nullable=True,
                    ),
                    ColumnSpec("P75 national", "p75_national", "float", nullable=True),
                    ColumnSpec("P90 national", "p90_national", "float", nullable=True),
                ),
                validators=(
                    v.Ordering(("mediane_delai_national", "p75_national", "p90_national")),
                    v.UniqueKey(("period",)),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="MAJ-02",
        section="maj-rescoring",
        title="Progression du stock des mises à jour « en cours » par mois",
        unit="dossiers",
        aggregation_strategy=AggregationStrategy.STOCK,
        supported_filters=frozenset(
            {"period", "region", "province", "milieu", "channel", "update_type"}
        ),
        supported_breakdowns=(
            BreakdownSpec("update_type"),
            BreakdownSpec("channel"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="update_type",
        measures=("value",),
        stock_field="maj_en_cours",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="MAJ-02",
                header_row=4,
                usecols="A:G",
                model=m.KpiMaj02,
                natural_key=("period", "update_type", "channel", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Mois / date d’arrêté", "period", "date"),
                    ColumnSpec("Type de mise à jour", "update_type"),
                    ColumnSpec("Canal", "channel"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de MAJ « en cours »", "maj_en_cours", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("maj_en_cours",)),
                    v.UniqueKey(
                        ("period", "update_type", "channel", "region", "province", "milieu")
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="MAJ-03",
        section="maj-rescoring",
        title="Progression des demandes de mise à jour initiées par les ménages",
        unit="demandes",
        aggregation_strategy=AggregationStrategy.STOCK,
        supported_filters=frozenset(
            {"period", "region", "province", "milieu", "channel", "update_type"}
        ),
        supported_breakdowns=(
            BreakdownSpec("update_type"),
            BreakdownSpec("channel"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="update_type",
        measures=("value",),
        stock_field="demandes_maj_initiees",
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="MAJ-03",
                header_row=4,
                usecols="A:G",
                model=m.KpiMaj03,
                natural_key=("period", "update_type", "channel", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Mois d’initiation", "period", "date"),
                    ColumnSpec("Type de mise à jour", "update_type"),
                    ColumnSpec("Canal", "channel"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de demandes de MAJ initiées", "demandes_maj_initiees", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("demandes_maj_initiees",)),
                    v.UniqueKey(
                        ("period", "update_type", "channel", "region", "province", "milieu")
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="MAJ-04",
        section="maj-rescoring",
        title="Taux de ménages non rescorés après une année",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset({"period", "region", "province", "milieu"}),
        supported_breakdowns=(
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="region",
        measures=("value",),
        ratio_windows=(("value", "menages_non_rescores_365j"),),
        denominator_field="menages_actifs",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="MAJ-04",
                header_row=4,
                usecols="A:F",
                model=m.KpiMaj04,
                natural_key=("period", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Date d’arrêté", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Nombre total de ménages actifs", "menages_actifs", "int"),
                    ColumnSpec(
                        "Nb de ménages dont le dernier rescoring >365 jours",
                        "menages_non_rescores_365j",
                        "int",
                    ),
                ),
                validators=(
                    v.NonNegative(("menages_actifs", "menages_non_rescores_365j")),
                    v.NumeratorLessEqualDenominator(
                        "menages_non_rescores_365j", "menages_actifs"
                    ),
                    v.UniqueKey(("period", "region", "province", "milieu")),
                ),
            ),
        ),
    )
)

# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="NOT-01",
        section="notification",
        title="Taux de chefs de ménage avec activité observée (OTP réussi ou notification reçue)",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset(
            {"period", "region", "province", "milieu", "gender", "age_band"}
        ),
        supported_breakdowns=(
            BreakdownSpec("gender"),
            BreakdownSpec("age_band"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="gender",
        measures=("value",),
        # The precomputed union column is the ONLY valid numerator -- never
        # chefs_avec_otp_reussi + chefs_avec_notification_recue, since a chef
        # can trigger both events and a naive sum would double-count the
        # overlap between the two populations.
        ratio_windows=(("value", "chefs_avec_activite_observee"),),
        denominator_field="chefs_avec_numero_enregistre",
        # OTP réussi / notification reçue are secondary, explanatory counts
        # displayed alongside the combined rate -- never summed into it.
        extra_measures=(
            ("otp_reussi", "chefs_avec_otp_reussi", "sum"),
            ("notification_recue", "chefs_avec_notification_recue", "sum"),
        ),
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="NOT-01",
                header_row=4,
                usecols="A:J",
                model=m.KpiNot01,
                natural_key=("period", "region", "province", "milieu", "gender", "age_band"),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Genre du chef de ménage", "gender"),
                    ColumnSpec("Tranche d’âge", "age_band"),
                    ColumnSpec(
                        "Chefs avec numéro enregistré",
                        "chefs_avec_numero_enregistre",
                        "int",
                    ),
                    ColumnSpec(
                        "Nb de Chefs avec ≥1 OTP réussi", "chefs_avec_otp_reussi", "int"
                    ),
                    ColumnSpec(
                        "Nombre de chefs avec au moins 1 notification reçue",
                        "chefs_avec_notification_recue",
                        "int",
                    ),
                    # Source header is missing its closing ")" verbatim in the
                    # workbook -- copied exactly as-is, per this file's own
                    # convention of matching source text byte-for-byte.
                    ColumnSpec(
                        "Chefs avec ≥1 activité observée (OTP réussi ou notification reçue",
                        "chefs_avec_activite_observee",
                        "int",
                    ),
                ),
                validators=(
                    v.NonNegative(
                        (
                            "chefs_avec_numero_enregistre",
                            "chefs_avec_otp_reussi",
                            "chefs_avec_notification_recue",
                            "chefs_avec_activite_observee",
                        )
                    ),
                    v.NumeratorLessEqualDenominator(
                        "chefs_avec_activite_observee", "chefs_avec_numero_enregistre"
                    ),
                    # A union can never be smaller than either of its
                    # components.
                    v.NumeratorLessEqualDenominator(
                        "chefs_avec_otp_reussi", "chefs_avec_activite_observee"
                    ),
                    v.NumeratorLessEqualDenominator(
                        "chefs_avec_notification_recue", "chefs_avec_activite_observee"
                    ),
                    v.UniqueKey(
                        ("period", "region", "province", "milieu", "gender", "age_band")
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="NOT-02",
        section="notification",
        title="Taux de livraison du courrier postal",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset({"period", "region", "province", "milieu", "mail_type"}),
        supported_breakdowns=(
            BreakdownSpec("mail_type"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="mail_type",
        measures=("value",),
        ratio_windows=(("value", "courriers_livres"),),
        denominator_field="courriers_envoyes_observables",
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="NOT-02",
                header_row=4,
                usecols="A:J",
                model=m.KpiNot02,
                natural_key=("period", "mail_type", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Mois d’envoi", "period", "date"),
                    ColumnSpec("Type de courrier", "mail_type"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de courriers envoyés observables",
                        "courriers_envoyes_observables",
                        "int",
                    ),
                    ColumnSpec("Nombre de courriers livrés", "courriers_livres", "int"),
                    ColumnSpec(
                        "Nombre non livrés / retournés",
                        "non_livres_retournes",
                        "int",
                        nullable=True,
                    ),
                    ColumnSpec(
                        "Nombre encore en acheminement",
                        "en_acheminement",
                        "int",
                        nullable=True,
                    ),
                    ColumnSpec(
                        "Motif principal de non-livraison",
                        "motif_principal_non_livraison",
                        "str",
                        nullable=True,
                    ),
                ),
                validators=(
                    v.NonNegative(
                        (
                            "courriers_envoyes_observables",
                            "courriers_livres",
                            "non_livres_retournes",
                            "en_acheminement",
                        )
                    ),
                    v.NumeratorLessEqualDenominator(
                        "courriers_livres", "courriers_envoyes_observables"
                    ),
                    v.SumEquals(
                        ("courriers_livres", "non_livres_retournes"),
                        "courriers_envoyes_observables",
                    ),
                    v.UniqueKey(("period", "mail_type", "region", "province", "milieu")),
                ),
            ),
        ),
    )
)

# ---------------------------------------------------------------------------
# Recours & réclamations
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="REC-01",
        section="recours-reclamations",
        title="Délai moyen de traitement des recours",
        unit="jours",
        aggregation_strategy=AggregationStrategy.WEIGHTED_MEAN,
        supported_filters=frozenset(
            {"period", "recourse_motive", "region", "province", "milieu"}
        ),
        supported_breakdowns=(
            BreakdownSpec("recourse_motive"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="recourse_motive",
        measures=("value",),
        weight_field="nb_decisions_finales",
        value_field="delai_moyen_jours",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="REC-01",
                header_row=4,
                usecols="A:G",
                model=m.KpiRec01,
                natural_key=("period", "recourse_motive", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Mois de dépôt", "period", "date"),
                    ColumnSpec("Motif du recours", "recourse_motive"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de recours avec décision finale",
                        "nb_decisions_finales",
                        "int",
                    ),
                    ColumnSpec("Délai moyen", "delai_moyen_jours", "float", nullable=True),
                ),
                validators=(
                    v.NonNegative(("nb_decisions_finales",)),
                    v.UniqueKey(
                        ("period", "recourse_motive", "region", "province", "milieu")
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="REC-02",
        section="recours-reclamations",
        title="Évolution du stock de recours « en cours »",
        unit="dossiers",
        aggregation_strategy=AggregationStrategy.STOCK,
        supported_filters=frozenset({"period", "recourse_motive", "region", "province"}),
        supported_breakdowns=(
            BreakdownSpec("recourse_motive"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
        ),
        default_breakdown="recourse_motive",
        measures=("value",),
        stock_field="recours_en_cours",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="REC-02",
                header_row=4,
                usecols="A:E",
                model=m.KpiRec02,
                natural_key=("period", "recourse_motive", "region", "province"),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec("Motif du recours", "recourse_motive"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec(
                        "Nombre de recours « en cours »", "recours_en_cours", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("recours_en_cours",)),
                    v.UniqueKey(("period", "recourse_motive", "region", "province")),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="REC-03",
        section="recours-reclamations",
        title="Part des recours acceptés",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset(
            {"period", "recourse_motive", "region", "province", "milieu"}
        ),
        supported_breakdowns=(
            BreakdownSpec("recourse_motive"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="recourse_motive",
        measures=("value",),
        ratio_windows=(("value", "recours_acceptes"),),
        denominator_field="recours_decision_finale",
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="REC-03",
                header_row=4,
                usecols="A:G",
                model=m.KpiRec03,
                natural_key=(
                    "period",
                    "recourse_motive",
                    "region",
                    "province",
                    "milieu",
                ),
                columns=(
                    ColumnSpec("Mois de décision", "period", "date"),
                    ColumnSpec("Motif du recours", "recourse_motive"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de recours avec décision finale",
                        "recours_decision_finale",
                        "int",
                    ),
                    ColumnSpec("Nombre de recours acceptés", "recours_acceptes", "int"),
                ),
                validators=(
                    v.NonNegative(("recours_decision_finale", "recours_acceptes")),
                    v.NumeratorLessEqualDenominator(
                        "recours_acceptes", "recours_decision_finale"
                    ),
                    v.UniqueKey(
                        ("period", "recourse_motive", "region", "province", "milieu")
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="REC-04",
        section="recours-reclamations",
        title="Délai de traitement des réclamations, Portail / CSC",
        unit="jours",
        aggregation_strategy=AggregationStrategy.WEIGHTED_MEAN,
        supported_filters=frozenset(
            {"period", "channel", "region", "province", "milieu"}
        ),
        supported_breakdowns=(
            BreakdownSpec("channel"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="channel",
        measures=("value",),
        weight_field="nb_reclamations_cloturees",
        value_field="delai_moyen_jours",
        lower_is_better=True,
        # "cloturés" (a flow, safe to sum across whatever rows are in a
        # group) and "en_cours" (a stock/snapshot -- must only ever reflect
        # the most recent period in a group, never accumulated across
        # periods; see `analytics.aggregate_latest`). Absorbs the concept
        # formerly tracked by the now-retired REC-07.
        extra_measures=(
            ("cloturés", "nb_reclamations_cloturees", "sum"),
            ("en_cours", "reclamations_en_cours", "latest"),
        ),
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="REC-04",
                header_row=4,
                usecols="A:I",
                model=m.KpiRec04,
                natural_key=("period", "channel", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec("Canal", "channel"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de réclamations clôturées pendant le mois",
                        "nb_reclamations_cloturees",
                        "int",
                    ),
                    ColumnSpec(
                        "Délai moyen des réclamations clôturées",
                        "delai_moyen_jours",
                        "float",
                        nullable=True,
                    ),
                    ColumnSpec(
                        "Nombre de réclamations « en cours » à fin de mois",
                        "reclamations_en_cours",
                        "int",
                        nullable=True,
                    ),
                    # "Date d'arrêté" is present in the sheet but intentionally
                    # left undeclared here: it's the exact cutoff date within
                    # "Mois" (redundant for our monthly-grouped trend), and
                    # `parse_table` silently drops any column read within
                    # `usecols` that has no matching ColumnSpec.
                ),
                validators=(
                    v.NonNegative(("nb_reclamations_cloturees", "reclamations_en_cours")),
                    v.UniqueKey(
                        ("period", "channel", "region", "province", "milieu")
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="REC-05",
        section="recours-reclamations",
        title=(
            "Taux de réclamations rapportées aux préinscriptions "
            "+ demandes de MAJ du même mois"
        ),
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset({"period", "region", "province", "milieu"}),
        supported_breakdowns=(
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="region",
        measures=("value",),
        ratio_windows=(("value", "reclamations"),),
        denominator_field=("preinscriptions", "demandes_maj"),
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="REC-05",
                header_row=4,
                usecols="A:G",
                model=m.KpiRec05,
                natural_key=("period", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Mois", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Nombre de réclamations", "reclamations", "int"),
                    ColumnSpec("Nombre de préinscriptions", "preinscriptions", "int"),
                    ColumnSpec(
                        "Nombre de demandes de mise à jour", "demandes_maj", "int"
                    ),
                ),
                validators=(
                    v.NonNegative(("reclamations", "preinscriptions", "demandes_maj")),
                    v.UniqueKey(("period", "region", "province", "milieu")),
                ),
            ),
        ),
    )
)

# ---------------------------------------------------------------------------
# Contrôle qualité
# ---------------------------------------------------------------------------

register(
    KpiSpec(
        code="CQD-01",
        section="controle-qualite",
        title="Taux de fraudes avérées parmi les suspicions de fraude",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset(
            {
                "period",
                "region",
                "province",
                "milieu",
                "suspicion_rule",
                "suspected_fraud_type",
            }
        ),
        supported_breakdowns=(
            BreakdownSpec("suspicion_rule"),
            BreakdownSpec("suspected_fraud_type"),
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="suspicion_rule",
        # Confirmed explicitly (not just left to the "month" default): the
        # "Période" header here is generic, unlike INS-03's explicit
        # "Trimestre", so CQD-01's monthly reference cadence is pinned down
        # in the catalogue rather than implied.
        period_grain="month",
        measures=("value",),
        ratio_windows=(("value", "fraudes_averees"),),
        denominator_field="suspicions_cloturees_evaluables",
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="CQD-01",
                header_row=4,
                usecols="A:I",
                model=m.KpiCqd01,
                natural_key=(
                    "period",
                    "suspicion_rule",
                    "suspected_fraud_type",
                    "region",
                    "province",
                    "milieu",
                ),
                columns=(
                    ColumnSpec("Période", "period", "date"),
                    ColumnSpec("Règle / source de suspicion", "suspicion_rule"),
                    ColumnSpec("Type de fraude suspectée", "suspected_fraud_type"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec(
                        "Nombre de suspicions clôturées",
                        "suspicions_cloturees_evaluables",
                        "int",
                    ),
                    ColumnSpec("Nombre de fraudes avérées", "fraudes_averees", "int"),
                    ColumnSpec(
                        "Nombre de suspicions en traitement",
                        "suspicions_en_traitement",
                        "int",
                        nullable=True,
                    ),
                ),
                validators=(
                    v.NonNegative(
                        (
                            "suspicions_cloturees_evaluables",
                            "fraudes_averees",
                            "suspicions_en_traitement",
                        )
                    ),
                    v.NumeratorLessEqualDenominator(
                        "fraudes_averees", "suspicions_cloturees_evaluables"
                    ),
                    v.UniqueKey(
                        (
                            "period",
                            "suspicion_rule",
                            "suspected_fraud_type",
                            "region",
                            "province",
                            "milieu",
                        )
                    ),
                ),
            ),
        ),
    )
)

register(
    KpiSpec(
        code="CQD-02",
        section="controle-qualite",
        title="Taux de ménages soupçonnés de fraude",
        unit="%",
        aggregation_strategy=AggregationStrategy.RATIO,
        supported_filters=frozenset({"period", "region", "province", "milieu"}),
        supported_breakdowns=(
            BreakdownSpec("region"),
            BreakdownSpec("province"),
            BreakdownSpec("milieu"),
        ),
        default_breakdown="region",
        # Rouge/orange/total are three parallel ratio windows sharing one
        # denominator (same pattern as ACC-01's 30j/90j) -- not a breakdown
        # dimension. "total" must stay last: `_headline()` reads
        # `ratio_windows[-1]` for the card's headline value/delta. A région
        # breakdown automatically returns {rouge, orange, total} per région
        # for free, since `aggregate_group`/`breakdown_by` splat every
        # ratio_windows key per group -- this is how the "barre empilée
        # Rouge/Orange par région" view is produced, no bespoke code needed.
        measures=("rouge", "orange", "total"),
        # "total" is derived as rouge + orange, not read from its own
        # "Nombre total de ménages soupçonnés" column -- that source column
        # is blank in the real workbook (rouge/orange are the only counts the
        # source team actually fills in); the derivation is a defined
        # algebraic identity (docs/KPI_CATALOG.md), not a fabricated figure.
        ratio_windows=(
            ("rouge", "menages_soupconnes_rouge"),
            ("orange", "menages_soupconnes_orange"),
            ("total", ("menages_soupconnes_rouge", "menages_soupconnes_orange")),
        ),
        denominator_field="menages_actifs",
        lower_is_better=True,
        tables=(
            SheetTableSpec(
                table_key="main",
                sheet_name="CQD-02",
                header_row=4,
                usecols="A:H",
                model=m.KpiCqd02,
                natural_key=("period", "region", "province", "milieu"),
                columns=(
                    ColumnSpec("Période", "period", "date"),
                    ColumnSpec("Région", "region"),
                    ColumnSpec("Province / Préfecture", "province"),
                    ColumnSpec("Milieu", "milieu"),
                    ColumnSpec("Nombre total de ménages actifs", "menages_actifs", "int"),
                    ColumnSpec(
                        "Nombre de ménages soupçonnés Rouge",
                        "menages_soupconnes_rouge",
                        "int",
                    ),
                    ColumnSpec(
                        "Nombre de ménages soupçonnés Orange",
                        "menages_soupconnes_orange",
                        "int",
                    ),
                    ColumnSpec(
                        "Nombre total de ménages soupçonnés",
                        "menages_distincts_soupconnes",
                        "int",
                        nullable=True,
                    ),
                ),
                validators=(
                    v.NonNegative(
                        (
                            "menages_actifs",
                            "menages_soupconnes_rouge",
                            "menages_soupconnes_orange",
                            "menages_distincts_soupconnes",
                        )
                    ),
                    # Rouge/orange are mutually exclusive categories. Their
                    # sum must never exceed the active-household base --
                    # the real enforceable bound, since the KPI's headline
                    # "total" is derived from rouge+orange, not read back
                    # from this often-blank column.
                    v.SumLessEqual(
                        ("menages_soupconnes_rouge", "menages_soupconnes_orange"),
                        "menages_actifs",
                    ),
                    # If the source *does* fill in its own total column,
                    # it must agree with rouge + orange -- skipped entirely
                    # when that column is blank (the common case today).
                    v.SumEquals(
                        ("menages_soupconnes_rouge", "menages_soupconnes_orange"),
                        "menages_distincts_soupconnes",
                    ),
                    v.UniqueKey(("period", "region", "province", "milieu")),
                ),
            ),
        ),
    )
)
