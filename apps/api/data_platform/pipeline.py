from __future__ import annotations

import csv
import hashlib
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

import duckdb
import pyarrow.ipc as arrow_ipc

logger = logging.getLogger("data-platform.pipeline")


@dataclass(frozen=True)
class SourceDefinition:
    logical_name: str
    relative_path: str
    columns: tuple[tuple[str, str], ...]
    required: bool = True
    physical_header: tuple[str, ...] | None = None


@dataclass
class BuildResult:
    content_hash: str
    version_key: str
    dataset_path: Path
    database_path: Path
    manifest_path: Path
    source_files: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    quality_checks: list[dict[str, Any]]
    row_counts: dict[str, int]
    period_start: date
    period_end: date
    products: dict[str, Any]


SOURCE_DEFINITIONS: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        "households",
        "menage.csv",
        (
            ("menage_ano", "BIGINT"),
            ("milieu", "VARCHAR"),
            ("region_id", "INTEGER"),
            ("region", "VARCHAR"),
            ("province_id", "INTEGER"),
            ("province", "VARCHAR"),
            ("commune_id", "INTEGER"),
            ("commune", "VARCHAR"),
            ("type_menage", "VARCHAR"),
            ("taille_menage", "INTEGER"),
            ("etat_matrimonial_cm", "VARCHAR"),
            ("genre_cm", "VARCHAR"),
            ("sexe_id", "INTEGER"),
            ("date_naissance_cm", "DATE"),
        ),
    ),
    SourceDefinition(
        "scores",
        "score.csv",
        (
            ("menage_ano", "BIGINT"),
            ("score_id_ano", "BIGINT"),
            ("type_demande", "VARCHAR"),
            ("score_corrige", "DOUBLE"),
            ("score_calcule", "DOUBLE"),
            ("date_calcul", "TIMESTAMP"),
        ),
    ),
    SourceDefinition(
        "beneficiary_events",
        "beneficiaire.csv",
        (
            ("menage_ano", "BIGINT"),
            ("partner_id", "VARCHAR"),
            ("motif", "VARCHAR"),
            ("date_insert", "TIMESTAMP"),
            ("actif", "BOOLEAN"),
        ),
    ),
    SourceDefinition("membership_asd", "asd.csv", (("menage_ano", "BIGINT"),)),
    SourceDefinition("membership_amot", "amot.csv", (("menage_ano", "BIGINT"),)),
    SourceDefinition("membership_amoa", "amoa.csv", (("menage_ano", "BIGINT"),)),
    SourceDefinition(
        "beneficiary_reasons",
        "ref_motif_beneficiaire.csv",
        (("motif", "VARCHAR"), ("label", "VARCHAR")),
        physical_header=("motif", ""),
    ),
    SourceDefinition(
        "score_variable_reference",
        "ref_variable.csv",
        (
            ("variable_id", "INTEGER"),
            ("name", "VARCHAR"),
            ("unused_1", "VARCHAR"),
            ("unused_2", "VARCHAR"),
            ("unused_3", "VARCHAR"),
        ),
        physical_header=("variable_id", "name", "", "", ""),
    ),
    SourceDefinition(
        "score_variables",
        "score_variable.csv",
        (
            ("score_id_ano", "BIGINT"),
            ("menage_ano", "BIGINT"),
            ("variable_id", "INTEGER"),
            ("score_variable_coeficient", "DOUBLE"),
            ("score_variable_valeur_calcule", "DOUBLE"),
            ("score_variable_valeur_corrige", "DOUBLE"),
        ),
        required=False,
    ),
)


class PipelineError(RuntimeError):
    pass


class RsuCsvPipeline:
    def __init__(
        self,
        *,
        source_path: Path,
        analytics_path: Path,
        pipeline_version: str,
        memory_limit: str,
        threads: int,
        temp_directory: Path,
        max_temp_directory_size: str,
        include_score_variables: bool,
    ) -> None:
        self.source_path = source_path
        self.analytics_path = analytics_path
        self.pipeline_version = pipeline_version
        self.memory_limit = memory_limit
        self.threads = threads
        self.temp_directory = temp_directory
        self.max_temp_directory_size = max_temp_directory_size
        self.include_score_variables = include_score_variables

    def build(self, batch_id: str) -> BuildResult:
        source_files, content_hash = self._inventory_source()
        version_key = f"{self.pipeline_version}-{content_hash[:12]}-{batch_id[:8]}"
        dataset_path = self.analytics_path / "releases" / version_key
        database_path = dataset_path / "analytics.duckdb"
        manifest_path = dataset_path / "manifest.json"

        if dataset_path.exists():
            shutil.rmtree(dataset_path)
        (dataset_path / "core").mkdir(parents=True, exist_ok=True)
        (dataset_path / "products" / "programmes-sociaux-rescoring").mkdir(
            parents=True, exist_ok=True
        )
        self.temp_directory.mkdir(parents=True, exist_ok=True)

        parameters = self._load_parameters()
        tuning = parameters.setdefault("tuning", {})
        tuning.update(
            {
                "cutoff_dt": "2024-03-01",
                "bucket_frequency_days": 30,
                "bucket_func": "mean_filtered",
                "score_floor": 5.0,
                "score_cap": 15.0,
                "compatibility_profile": "julia-30d-v1",
            }
        )

        con = duckdb.connect(str(database_path))
        artifacts: list[dict[str, Any]] = []
        row_counts: dict[str, int] = {}
        try:
            self._configure(con)
            self._build_core(con, dataset_path, artifacts, row_counts)
            self._build_derived(
                con,
                dataset_path,
                artifacts,
                row_counts,
                parameters=parameters,
            )
            checks = self._quality_checks(con, row_counts)
            blocking = [item for item in checks if item["severity"] == "error" and not item["passed"]]
            if blocking:
                names = ", ".join(item["check_key"] for item in blocking)
                raise PipelineError(f"blocking data quality checks failed: {names}")

            period_row = con.execute(
                "SELECT min(CAST(date_calcul AS DATE)), max(CAST(date_calcul AS DATE)) "
                "FROM fact_score_event WHERE date_calcul IS NOT NULL"
            ).fetchone()
            if period_row is None:
                raise PipelineError("score.csv has no usable date_calcul values")
            period_start, period_end = period_row
            if period_start is None or period_end is None:
                raise PipelineError("score.csv has no usable date_calcul values")

            source_count_map = {
                "households": row_counts["dim_household"],
                "scores": row_counts["fact_score_event"],
                "beneficiary_events": row_counts["fact_beneficiary_event"],
                "membership_asd": self._scalar(con, "SELECT count(*) FROM bridge_program_household WHERE program_code='ASD'"),
                "membership_amot": self._scalar(con, "SELECT count(*) FROM bridge_program_household WHERE program_code='AMOT'"),
                "membership_amoa": self._scalar(con, "SELECT count(*) FROM bridge_program_household WHERE program_code='AMOA'"),
                "beneficiary_reasons": row_counts["dim_beneficiary_reason"],
                "score_variable_reference": row_counts["dim_score_variable"],
                "score_variables": row_counts.get("fact_score_variable_event"),
            }
            for item in source_files:
                item["row_count"] = source_count_map.get(item["logical_name"])

            manifest = {
                "schema_version": "1.0",
                "pipeline_version": self.pipeline_version,
                "version_key": version_key,
                "content_hash": content_hash,
                "built_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "source": {
                    "type": "csv-directory",
                    "files": source_files,
                },
                "parameters": parameters,
                "period": {"start": str(period_start), "end": str(period_end)},
                "row_counts": row_counts,
                "quality_checks": checks,
                "artifacts": [
                    {key: value for key, value in item.items() if key != "schema_json"}
                    for item in artifacts
                ],
            }
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        except Exception:
            con.close()
            shutil.rmtree(dataset_path, ignore_errors=True)
            raise
        else:
            con.close()

        artifacts.append(
            self._artifact_record(
                dataset_path=dataset_path,
                path=database_path,
                layer="catalog",
                name="analytics_catalog",
                format_name="duckdb",
                row_count=None,
                schema=[],
            )
        )
        artifacts.append(
            self._artifact_record(
                dataset_path=dataset_path,
                path=manifest_path,
                layer="manifest",
                name="release_manifest",
                format_name="json",
                row_count=None,
                schema=[],
            )
        )

        products = {
            "programmes-sociaux-rescoring": {
                "version": "programmes-sociaux-rescoring-v1",
                "tables": [
                    "fact_program_crossing",
                    "mart_program_flow_daily",
                    "mart_program_volatility",
                ],
            }
        }
        return BuildResult(
            content_hash=content_hash,
            version_key=version_key,
            dataset_path=dataset_path,
            database_path=database_path,
            manifest_path=manifest_path,
            source_files=source_files,
            artifacts=artifacts,
            quality_checks=checks,
            row_counts=row_counts,
            period_start=period_start,
            period_end=period_end,
            products=products,
        )

    def _inventory_source(self) -> tuple[list[dict[str, Any]], str]:
        if not self.source_path.is_dir():
            raise PipelineError(f"configured CSV source directory does not exist: {self.source_path}")
        inventory: list[dict[str, Any]] = []
        delivery_hash = hashlib.sha256()
        for definition in SOURCE_DEFINITIONS:
            if definition.logical_name == "score_variables" and not self.include_score_variables:
                continue
            path = self.source_path / definition.relative_path
            required = definition.required or definition.logical_name == "score_variables"
            if not path.is_file():
                if required:
                    raise PipelineError(f"required source file is missing: {definition.relative_path}")
                continue
            header = self._read_header(path)
            expected = list(
                definition.physical_header
                or tuple(column[0] for column in definition.columns)
            )
            normalized = [column.lstrip("\ufeff") for column in header]
            if normalized[: len(expected)] != expected:
                raise PipelineError(
                    f"unexpected columns in {definition.relative_path}: "
                    f"expected {expected}, received {normalized}"
                )
            digest = self._sha256(path)
            delivery_hash.update(definition.logical_name.encode())
            delivery_hash.update(digest.encode())
            inventory.append(
                {
                    "logical_name": definition.logical_name,
                    "relative_path": definition.relative_path,
                    "sha256": digest,
                    "byte_size": path.stat().st_size,
                    "row_count": None,
                    "required": required,
                    "schema_json": {
                        "columns": [
                            {"name": name, "type": type_name}
                            for name, type_name in definition.columns
                        ]
                    },
                    "profile_json": {},
                }
            )
        parameters_path = self.source_path / "parameters" / "rsu_parameters.json"
        if not parameters_path.is_file():
            raise PipelineError(
                "required source parameter file is missing: "
                "parameters/rsu_parameters.json"
            )
        parameters_digest = self._sha256(parameters_path)
        delivery_hash.update(b"parameters")
        delivery_hash.update(parameters_digest.encode())
        inventory.append(
            {
                "logical_name": "parameters",
                "relative_path": "parameters/rsu_parameters.json",
                "sha256": parameters_digest,
                "byte_size": parameters_path.stat().st_size,
                "row_count": None,
                "required": True,
                "schema_json": {"type": "json", "schema_version": "2.3"},
                "profile_json": {},
            }
        )
        delivery_hash.update(self.pipeline_version.encode())
        delivery_hash.update(b"julia-30d-v1")
        delivery_hash.update(str(self.include_score_variables).encode())
        return inventory, delivery_hash.hexdigest()

    def _build_core(
        self,
        con: duckdb.DuckDBPyConnection,
        dataset_path: Path,
        artifacts: list[dict[str, Any]],
        row_counts: dict[str, int],
    ) -> None:
        household = self._read_csv_sql("households")
        self._materialize(
            con,
            dataset_path,
            "dim_household",
            f"""
            SELECT menage_ano, nullif(trim(milieu), '') AS milieu,
                   region_id, nullif(trim(region), '') AS region,
                   province_id, nullif(trim(province), '') AS province,
                   commune_id, nullif(trim(commune), '') AS commune,
                   nullif(trim(type_menage), '') AS type_menage, taille_menage,
                   nullif(trim(etat_matrimonial_cm), '') AS etat_matrimonial_cm,
                   nullif(trim(genre_cm), '') AS genre_cm, sexe_id, date_naissance_cm
            FROM {household}
            """,
            "core",
            artifacts,
            row_counts,
        )
        self._materialize(
            con,
            dataset_path,
            "dim_household_current",
            """
            SELECT * EXCLUDE (_row_number)
            FROM (
                SELECT *, row_number() OVER (
                    PARTITION BY menage_ano
                    ORDER BY region_id NULLS LAST, province_id NULLS LAST, commune_id NULLS LAST
                ) AS _row_number
                FROM dim_household
            )
            WHERE _row_number = 1
            """,
            "core",
            artifacts,
            row_counts,
        )

        scores = self._read_csv_sql("scores")
        self._materialize(
            con,
            dataset_path,
            "fact_score_event",
            f"""
            SELECT menage_ano, score_id_ano, nullif(trim(type_demande), '') AS type_demande,
                   score_corrige, score_calcule,
                   coalesce(score_corrige, score_calcule) AS score_final,
                   date_calcul,
                   coalesce(score_corrige, score_calcule) BETWEEN 5.0 AND 15.0 AS is_valid_score
            FROM {scores}
            """,
            "core",
            artifacts,
            row_counts,
        )

        beneficiary = self._read_csv_sql("beneficiary_events")
        self._materialize(
            con,
            dataset_path,
            "fact_beneficiary_event",
            f"""
            SELECT menage_ano, upper(trim(partner_id)) AS program_code,
                   motif, date_insert, actif AS is_active
            FROM {beneficiary}
            """,
            "core",
            artifacts,
            row_counts,
        )

        membership_parts: list[str] = []
        for logical_name, code in (
            ("membership_asd", "ASD"),
            ("membership_amot", "AMOT"),
            ("membership_amoa", "AMOA"),
        ):
            membership_parts.append(
                f"SELECT DISTINCT menage_ano, '{code}' AS program_code "
                f"FROM {self._read_csv_sql(logical_name)} WHERE menage_ano IS NOT NULL"
            )
        self._materialize(
            con,
            dataset_path,
            "bridge_program_household",
            " UNION ALL ".join(membership_parts),
            "core",
            artifacts,
            row_counts,
        )

        reasons = self._read_csv_sql("beneficiary_reasons")
        self._materialize(
            con,
            dataset_path,
            "dim_beneficiary_reason",
            f"SELECT motif, nullif(trim(label), '') AS label FROM {reasons} WHERE motif IS NOT NULL",
            "core",
            artifacts,
            row_counts,
        )
        variables = self._read_csv_sql("score_variable_reference")
        self._materialize(
            con,
            dataset_path,
            "dim_score_variable",
            f"SELECT variable_id, nullif(trim(name), '') AS name FROM {variables} WHERE variable_id IS NOT NULL",
            "core",
            artifacts,
            row_counts,
        )

        score_variable_path = self.source_path / "score_variable.csv"
        if self.include_score_variables and score_variable_path.is_file():
            score_variables = self._read_csv_sql("score_variables")
            self._materialize(
                con,
                dataset_path,
                "fact_score_variable_event",
                f"""
                SELECT score_id_ano, menage_ano, variable_id,
                       score_variable_coeficient,
                       score_variable_valeur_calcule,
                       score_variable_valeur_corrige,
                       coalesce(score_variable_valeur_corrige, score_variable_valeur_calcule)
                           AS score_variable_final
                FROM {score_variables}
                """,
                "core-extended",
                artifacts,
                row_counts,
            )

    def _build_derived(
        self,
        con: duckdb.DuckDBPyConnection,
        dataset_path: Path,
        artifacts: list[dict[str, Any]],
        row_counts: dict[str, int],
        *,
        parameters: dict[str, Any],
    ) -> None:
        tuning = parameters["tuning"]
        cutoff = str(tuning["cutoff_dt"])
        bucket_days = int(tuning["bucket_frequency_days"])
        floor_score = float(tuning["score_floor"])
        cap_score = float(tuning["score_cap"])

        self._materialize(
            con,
            dataset_path,
            "fact_score_transition",
            f"""
            WITH bucketed AS (
                SELECT menage_ano,
                       floor(date_diff('day', DATE '{cutoff}', CAST(date_calcul AS DATE)) / {bucket_days}.0)::INTEGER AS bucket_number,
                       avg(score_final) AS score_bucket,
                       first(score_id_ano ORDER BY date_calcul, score_id_ano) AS bucket_score_id1,
                       last(score_id_ano ORDER BY date_calcul, score_id_ano) AS bucket_score_id2,
                       min(date_calcul) AS bucket_dt1,
                       max(date_calcul) AS bucket_dt2
                FROM fact_score_event
                WHERE date_calcul >= TIMESTAMP '{cutoff}'
                  AND score_final BETWEEN {floor_score} AND {cap_score}
                GROUP BY menage_ano, bucket_number
            ), lagged AS (
                SELECT *,
                       lag(score_bucket) OVER household_history AS score_bucket_prev,
                       lag(bucket_dt2) OVER household_history AS date_calcul_prev
                FROM bucketed
                WINDOW household_history AS (PARTITION BY menage_ano ORDER BY bucket_number)
            )
            SELECT menage_ano, bucket_number, bucket_score_id1, bucket_score_id2,
                   bucket_dt1, bucket_dt2 AS date_calcul, date_calcul_prev,
                   score_bucket_prev, score_bucket,
                   score_bucket - score_bucket_prev AS delta_ise,
                   date_diff('day', CAST(date_calcul_prev AS DATE), CAST(bucket_dt2 AS DATE)) AS delta_days,
                   CASE WHEN date_diff('day', CAST(date_calcul_prev AS DATE), CAST(bucket_dt2 AS DATE)) > 0
                        THEN (score_bucket - score_bucket_prev) /
                             date_diff('day', CAST(date_calcul_prev AS DATE), CAST(bucket_dt2 AS DATE))
                   END AS adjusted_delta_ise
            FROM lagged
            WHERE score_bucket_prev IS NOT NULL
            """,
            "derived",
            artifacts,
            row_counts,
        )

        threshold_rows = []
        for item in parameters.get("program_thresholds", []):
            program = str(item["program"]).upper().replace("'", "''")
            threshold_rows.append(f"('{program}', {float(item['threshold'])})")
        thresholds = ", ".join(threshold_rows)
        if not thresholds:
            raise PipelineError("parameters contain no program_thresholds")

        self._materialize(
            con,
            dataset_path,
            "dim_program_threshold",
            f"SELECT * FROM (VALUES {thresholds}) AS t(program_code, threshold)",
            "derived",
            artifacts,
            row_counts,
        )

        self._materialize(
            con,
            dataset_path,
            "fact_program_crossing",
            """
            WITH classified AS (
                SELECT t.menage_ano, m.program_code, t.date_calcul,
                       t.date_calcul_prev, t.score_bucket_prev, t.score_bucket,
                       t.delta_ise, t.adjusted_delta_ise, t.delta_days,
                       p.threshold,
                       CASE
                           WHEN t.score_bucket_prev <= p.threshold AND t.score_bucket > p.threshold THEN 'out'
                           WHEN t.score_bucket_prev > p.threshold AND t.score_bucket <= p.threshold THEN 'in'
                       END AS cross_direction
                FROM fact_score_transition t
                INNER JOIN bridge_program_household m USING (menage_ano)
                INNER JOIN dim_program_threshold p USING (program_code)
            )
            SELECT c.*, h.milieu, h.region_id, h.region, h.province_id, h.province,
                   h.commune_id, h.commune
            FROM classified c
            LEFT JOIN dim_household_current h USING (menage_ano)
            WHERE cross_direction IS NOT NULL
            """,
            "product",
            artifacts,
            row_counts,
        )

        self._materialize(
            con,
            dataset_path,
            "mart_program_flow_daily",
            """
            SELECT program_code, CAST(date_calcul AS DATE) AS event_date,
                   region_id, region, province_id, province,
                   count(*) FILTER (WHERE cross_direction = 'in') AS entries,
                   count(*) FILTER (WHERE cross_direction = 'out') AS exits,
                   count(*) FILTER (WHERE cross_direction = 'in') -
                       count(*) FILTER (WHERE cross_direction = 'out') AS net,
                   avg(delta_ise) FILTER (WHERE cross_direction = 'in') AS average_entry_delta,
                   avg(delta_ise) FILTER (WHERE cross_direction = 'out') AS average_exit_delta
            FROM fact_program_crossing
            GROUP BY program_code, event_date, region_id, region, province_id, province
            """,
            "product",
            artifacts,
            row_counts,
            export_arrow=True,
        )

        self._materialize(
            con,
            dataset_path,
            "mart_program_volatility",
            """
            WITH binned AS (
                SELECT program_code, cross_direction, region_id, region, province_id, province,
                       CASE
                           WHEN abs(delta_ise) < 0.01 THEN '<1'
                           WHEN abs(delta_ise) < 0.05 THEN '1-5'
                           WHEN abs(delta_ise) < 0.10 THEN '5-10'
                           WHEN abs(delta_ise) < 0.20 THEN '10-20'
                           WHEN abs(delta_ise) < 0.30 THEN '20-30'
                           WHEN abs(delta_ise) < 0.50 THEN '30-50'
                           ELSE '51+'
                       END AS volatility_band,
                       CASE
                           WHEN abs(delta_ise) < 0.01 THEN 1
                           WHEN abs(delta_ise) < 0.05 THEN 2
                           WHEN abs(delta_ise) < 0.10 THEN 3
                           WHEN abs(delta_ise) < 0.20 THEN 4
                           WHEN abs(delta_ise) < 0.30 THEN 5
                           WHEN abs(delta_ise) < 0.50 THEN 6
                           ELSE 7
                       END AS band_order
                FROM fact_program_crossing
            )
            SELECT program_code, cross_direction, region_id, region, province_id, province,
                   volatility_band, band_order, count(*) AS crossings
            FROM binned
            GROUP BY ALL
            """,
            "product",
            artifacts,
            row_counts,
            export_arrow=True,
        )

    def _quality_checks(
        self, con: duckdb.DuckDBPyConnection, row_counts: dict[str, int]
    ) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        def add(
            key: str,
            severity: str,
            passed: bool,
            observed: Any,
            expected: Any,
            details: dict[str, Any] | None = None,
        ) -> None:
            checks.append(
                {
                    "check_key": key,
                    "severity": severity,
                    "passed": passed,
                    "observed_value": str(observed),
                    "expected_value": str(expected),
                    "details_json": details or {},
                }
            )

        for name in (
            "dim_household",
            "fact_score_event",
            "fact_beneficiary_event",
            "bridge_program_household",
        ):
            observed = row_counts[name]
            add(f"{name}.not_empty", "error", observed > 0, observed, "> 0")

        duplicate_households = self._scalar(
            con,
            "SELECT count(*) - count(DISTINCT menage_ano) FROM dim_household",
        )
        add(
            "dim_household.unique_key",
            "warning",
            duplicate_households == 0,
            duplicate_households,
            0,
            {"policy": "preserved in canonical data; dashboard queries use distinct households"},
        )
        duplicate_scores = self._scalar(
            con,
            "SELECT count(*) - count(DISTINCT score_id_ano) FROM fact_score_event",
        )
        add(
            "fact_score_event.unique_score_id",
            "warning",
            duplicate_scores == 0,
            duplicate_scores,
            0,
            {"policy": "preserved for Julia compatibility"},
        )
        out_of_range = self._scalar(
            con,
            "SELECT count(*) FROM fact_score_event WHERE score_final IS NOT NULL AND NOT is_valid_score",
        )
        add(
            "fact_score_event.valid_range",
            "warning",
            out_of_range == 0,
            out_of_range,
            0,
            {"valid_range": [5.0, 15.0], "policy": "excluded from rescoring transitions"},
        )
        score_orphans = self._scalar(
            con,
            """
            SELECT count(*) FROM fact_score_event s
            LEFT JOIN dim_household h USING (menage_ano)
            WHERE h.menage_ano IS NULL
            """,
        )
        add(
            "fact_score_event.household_fk",
            "warning",
            score_orphans == 0,
            score_orphans,
            0,
            {"policy": "retained in core; excluded from territorial results"},
        )
        membership_orphans = self._scalar(
            con,
            """
            SELECT count(*) FROM bridge_program_household m
            LEFT JOIN dim_household h USING (menage_ano)
            WHERE h.menage_ano IS NULL
            """,
        )
        add(
            "bridge_program_household.household_fk",
            "warning",
            membership_orphans == 0,
            membership_orphans,
            0,
            {"policy": "retained in core; excluded from territorial results"},
        )
        return checks

    def _materialize(
        self,
        con: duckdb.DuckDBPyConnection,
        dataset_path: Path,
        table_name: str,
        query: str,
        layer: str,
        artifacts: list[dict[str, Any]],
        row_counts: dict[str, int],
        *,
        export_arrow: bool = False,
    ) -> None:
        directory = (
            dataset_path / "products" / "programmes-sociaux-rescoring"
            if layer == "product"
            else dataset_path / "core"
        )
        directory.mkdir(parents=True, exist_ok=True)
        parquet_path = directory / f"{table_name}.parquet"
        sql_path = self._sql_path(parquet_path)
        logger.info("Building %s", table_name)
        con.execute(
            f"COPY ({query}) TO '{sql_path}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 250000)"
        )
        con.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{sql_path}')")
        count = self._scalar(con, f"SELECT count(*) FROM {table_name}")
        row_counts[table_name] = count
        schema = [
            {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
            for row in con.execute(f"DESCRIBE {table_name}").fetchall()
        ]
        artifacts.append(
            self._artifact_record(
                dataset_path=dataset_path,
                path=parquet_path,
                layer=layer,
                name=table_name,
                format_name="parquet",
                row_count=count,
                schema=schema,
            )
        )
        if export_arrow:
            arrow_path = directory / f"{table_name}.arrow"
            reader = con.execute(f"SELECT * FROM {table_name}").fetch_record_batch(65536)
            with (
                arrow_path.open("wb") as stream,
                arrow_ipc.new_file(stream, reader.schema) as writer,
            ):
                for batch in reader:
                    writer.write_batch(batch)
            artifacts.append(
                self._artifact_record(
                    dataset_path=dataset_path,
                    path=arrow_path,
                    layer=layer,
                    name=f"{table_name}_arrow",
                    format_name="arrow",
                    row_count=count,
                    schema=schema,
                )
            )

    def _artifact_record(
        self,
        *,
        dataset_path: Path,
        path: Path,
        layer: str,
        name: str,
        format_name: str,
        row_count: int | None,
        schema: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "product_build_id": None,
            "layer": layer,
            "artifact_name": name,
            "format": format_name,
            "relative_path": str(path.relative_to(dataset_path)),
            "sha256": self._sha256(path),
            "byte_size": path.stat().st_size,
            "row_count": row_count,
            "schema_json": {"columns": schema},
        }

    def _configure(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute(f"SET memory_limit = '{self.memory_limit.replace(chr(39), '')}'")
        con.execute(f"SET threads = {max(1, self.threads)}")
        con.execute(f"SET temp_directory = '{self._sql_path(self.temp_directory)}'")
        con.execute(
            "SET max_temp_directory_size = "
            f"'{self.max_temp_directory_size.replace(chr(39), '')}'"
        )
        con.execute("SET preserve_insertion_order = false")

    def _read_csv_sql(self, logical_name: str) -> str:
        definition = next(item for item in SOURCE_DEFINITIONS if item.logical_name == logical_name)
        path = self._sql_path(self.source_path / definition.relative_path)
        columns = ", ".join(
            f"'{name.replace(chr(39), chr(39) * 2)}': '{type_name}'"
            for name, type_name in definition.columns
        )
        return (
            f"read_csv('{path}', header=false, skip=1, columns={{{columns}}}, "
            "nullstr='', strict_mode=true, parallel=true)"
        )

    def _load_parameters(self) -> dict[str, Any]:
        path = self.source_path / "parameters" / "rsu_parameters.json"
        if not path.is_file():
            raise PipelineError(f"required source parameter file is missing: {path}")
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise PipelineError("rsu_parameters.json must contain a JSON object")
        return cast(dict[str, Any], value)

    @staticmethod
    def _read_header(path: Path) -> list[str]:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return next(csv.reader(stream))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(8 * 1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _sql_path(path: Path) -> str:
        return str(path.resolve()).replace("'", "''")

    @staticmethod
    def _scalar(con: duckdb.DuckDBPyConnection, query: str) -> int:
        row = con.execute(query).fetchone()
        if row is None:
            raise PipelineError(f"aggregate query returned no row: {query}")
        value = row[0]
        return int(value)
