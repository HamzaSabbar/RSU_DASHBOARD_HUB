from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from data_platform.schemas import AnalyticsFilters


class AnalyticsCatalogError(RuntimeError):
    pass


def cache_key(release_key: str, endpoint: str, payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return f"{release_key}:{endpoint}:{normalized}"


class AnalyticsQueryService:
    def __init__(self, database_path: Path, *, threads: int = 2) -> None:
        self.database_path = database_path
        self.threads = max(1, threads)

    def filter_options(self, release_key: str) -> dict[str, Any]:
        with self._connect() as con:
            period = con.execute(
                "SELECT greatest(min(CAST(date_calcul AS DATE)), DATE '2024-03-01'), "
                "max(CAST(date_calcul AS DATE)) "
                "FROM fact_score_event WHERE date_calcul IS NOT NULL"
            ).fetchone()
            regions = self._rows(
                con,
                """
                SELECT DISTINCT region_id AS id, region AS label, NULL::INTEGER AS parent_id
                FROM dim_household_current
                WHERE region_id IS NOT NULL AND region IS NOT NULL
                ORDER BY label
                """,
            )
            provinces = self._rows(
                con,
                """
                SELECT DISTINCT province_id AS id, province AS label, region_id AS parent_id
                FROM dim_household_current
                WHERE province_id IS NOT NULL AND province IS NOT NULL
                ORDER BY label
                """,
            )
        if period is None or period[0] is None or period[1] is None:
            raise AnalyticsCatalogError("active catalog has no score period")
        return {
            "release_key": release_key,
            "period_start": period[0],
            "period_end": period[1],
            "subjects": [
                {"value": "ALL", "label": "ASD + AMO T"},
                {"value": "ASD", "label": "ASD"},
                {"value": "AMOT", "label": "AMO T"},
            ],
            "regions": regions,
            "provinces": provinces,
        }

    def social_programs_dashboard(
        self, release_key: str, filters: AnalyticsFilters
    ) -> dict[str, Any]:
        where_sql, params = self._crossing_filter(filters)
        period_expression = {
            "day": "CAST(c.date_calcul AS DATE)",
            "week": "CAST(date_trunc('week', c.date_calcul) AS DATE)",
            "month": "CAST(date_trunc('month', c.date_calcul) AS DATE)",
            "quarter": "CAST(date_trunc('quarter', c.date_calcul) AS DATE)",
        }[filters.granularity]

        with self._connect() as con:
            flow = self._rows(
                con,
                f"""
                SELECT c.program_code, {period_expression} AS period,
                       count(*) FILTER (WHERE c.cross_direction='in') AS entries,
                       count(*) FILTER (WHERE c.cross_direction='out') AS exits,
                       count(*) FILTER (WHERE c.cross_direction='in') -
                           count(*) FILTER (WHERE c.cross_direction='out') AS net
                FROM fact_program_crossing c
                WHERE {where_sql}
                GROUP BY c.program_code, period
                ORDER BY period, c.program_code
                """,
                params,
            )
            program_totals = self._rows(
                con,
                f"""
                SELECT c.program_code,
                       count(*) FILTER (WHERE c.cross_direction='in') AS entries,
                       count(*) FILTER (WHERE c.cross_direction='out') AS exits,
                       count(*) FILTER (WHERE c.cross_direction='in') -
                           count(*) FILTER (WHERE c.cross_direction='out') AS net
                FROM fact_program_crossing c
                WHERE {where_sql}
                GROUP BY c.program_code
                ORDER BY c.program_code
                """,
                params,
            )
            eligibility = self._eligibility(con, filters)
            eligible_by_program = {
                str(item["program_code"]): int(item["eligible_households"])
                for item in eligibility
            }
            for item in program_totals:
                item["eligible_households"] = eligible_by_program.get(
                    str(item["program_code"]), 0
                )

            volatility = self._rows(
                con,
                f"""
                WITH binned AS (
                    SELECT c.program_code,
                           CASE
                               WHEN abs(c.delta_ise) < 0.01 THEN '<1'
                               WHEN abs(c.delta_ise) < 0.05 THEN '1-5'
                               WHEN abs(c.delta_ise) < 0.10 THEN '5-10'
                               WHEN abs(c.delta_ise) < 0.20 THEN '10-20'
                               WHEN abs(c.delta_ise) < 0.30 THEN '20-30'
                               WHEN abs(c.delta_ise) < 0.50 THEN '30-50'
                               ELSE '51+'
                           END AS band,
                           CASE
                               WHEN abs(c.delta_ise) < 0.01 THEN 1
                               WHEN abs(c.delta_ise) < 0.05 THEN 2
                               WHEN abs(c.delta_ise) < 0.10 THEN 3
                               WHEN abs(c.delta_ise) < 0.20 THEN 4
                               WHEN abs(c.delta_ise) < 0.30 THEN 5
                               WHEN abs(c.delta_ise) < 0.50 THEN 6
                               ELSE 7
                           END AS band_order
                    FROM fact_program_crossing c
                    WHERE {where_sql}
                )
                SELECT program_code, band, band_order, count(*) AS crossings,
                       round(100.0 * count(*) /
                           sum(count(*)) OVER (PARTITION BY program_code), 2) AS percentage
                FROM binned
                GROUP BY program_code, band, band_order
                ORDER BY band_order, program_code
                """,
                params,
            )
            territories = self._rows(
                con,
                f"""
                SELECT c.province_id, coalesce(c.province, 'Non renseignée') AS province,
                       count(*) FILTER (WHERE c.cross_direction='in') AS entries,
                       count(*) FILTER (WHERE c.cross_direction='out') AS exits,
                       count(*) FILTER (WHERE c.cross_direction='in') -
                           count(*) FILTER (WHERE c.cross_direction='out') AS net
                FROM fact_program_crossing c
                WHERE {where_sql}
                GROUP BY c.province_id, c.province
                ORDER BY abs(net) DESC, province
                LIMIT 20
                """,
                params,
            )

        # The combined ALL count is calculated separately so households in both
        # programs are not double-counted.
        if filters.subject == "ALL":
            total_eligible = self._combined_eligibility(filters)
        else:
            total_eligible = sum(eligible_by_program.values())

        return {
            "release_key": release_key,
            "filters": filters.model_dump(mode="json"),
            "summary": {
                "eligible_households": total_eligible,
                "programs": program_totals,
            },
            "flow": flow,
            "volatility": volatility,
            "territories": territories,
            "methodology": {
                "crossing_scope": "current program membership",
                "score_bucket": "30-day mean of scores between 5 and 15",
                "cutoff_date": "2024-03-01",
                "thresholds": {"ASD": 9.743001, "AMOT": 9.3264284},
                "eligibility": "latest valid score on or before selected end date",
            },
        }

    def _eligibility(
        self, con: duckdb.DuckDBPyConnection, filters: AnalyticsFilters
    ) -> list[dict[str, Any]]:
        subject_sql, subject_params = self._subject_filter(filters.subject, "m.program_code")
        geo_sql, geo_params = self._geography_filter(filters, "h")
        params: list[Any] = [filters.end_date, *subject_params, *geo_params]
        return self._rows(
            con,
            f"""
            WITH latest AS (
                SELECT menage_ano, arg_max(score_final, date_calcul) AS latest_score
                FROM fact_score_event
                WHERE is_valid_score AND CAST(date_calcul AS DATE) <= ?
                GROUP BY menage_ano
            )
            SELECT m.program_code, count(DISTINCT l.menage_ano) AS eligible_households
            FROM latest l
            INNER JOIN bridge_program_household m USING (menage_ano)
            INNER JOIN dim_program_threshold t USING (program_code)
            INNER JOIN dim_household_current h USING (menage_ano)
            WHERE l.latest_score <= t.threshold AND {subject_sql} AND {geo_sql}
            GROUP BY m.program_code
            ORDER BY m.program_code
            """,
            params,
        )

    def _combined_eligibility(self, filters: AnalyticsFilters) -> int:
        geo_sql, geo_params = self._geography_filter(filters, "h")
        with self._connect() as con:
            row = con.execute(
                f"""
                WITH latest AS (
                    SELECT menage_ano, arg_max(score_final, date_calcul) AS latest_score
                    FROM fact_score_event
                    WHERE is_valid_score AND CAST(date_calcul AS DATE) <= ?
                    GROUP BY menage_ano
                )
                SELECT count(DISTINCT l.menage_ano)
                FROM latest l
                INNER JOIN bridge_program_household m USING (menage_ano)
                INNER JOIN dim_program_threshold t USING (program_code)
                INNER JOIN dim_household_current h USING (menage_ano)
                WHERE m.program_code IN ('ASD', 'AMOT')
                  AND l.latest_score <= t.threshold AND {geo_sql}
                """,
                [filters.end_date, *geo_params],
            ).fetchone()
            if row is None:
                raise AnalyticsCatalogError("eligibility query returned no result")
            return int(row[0])

    def _crossing_filter(self, filters: AnalyticsFilters) -> tuple[str, list[Any]]:
        subject_sql, subject_params = self._subject_filter(filters.subject, "c.program_code")
        geo_sql, geo_params = self._geography_filter(filters, "c")
        return (
            f"CAST(c.date_calcul AS DATE) BETWEEN ? AND ? AND {subject_sql} AND {geo_sql}",
            [filters.start_date, filters.end_date, *subject_params, *geo_params],
        )

    @staticmethod
    def _subject_filter(subject: str, column: str) -> tuple[str, list[Any]]:
        if subject == "ALL":
            return f"{column} IN ('ASD', 'AMOT')", []
        return f"{column} = ?", [subject]

    @staticmethod
    def _geography_filter(
        filters: AnalyticsFilters, alias: str
    ) -> tuple[str, list[Any]]:
        clauses = ["TRUE"]
        params: list[Any] = []
        if filters.region_id is not None:
            clauses.append(f"{alias}.region_id = ?")
            params.append(filters.region_id)
        if filters.province_id is not None:
            clauses.append(f"{alias}.province_id = ?")
            params.append(filters.province_id)
        return " AND ".join(clauses), params

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if not self.database_path.is_file():
            raise AnalyticsCatalogError(
                f"published DuckDB catalog is unavailable: {self.database_path}"
            )
        con = duckdb.connect(str(self.database_path), read_only=True)
        con.execute(f"SET threads = {self.threads}")
        return con

    @staticmethod
    def _rows(
        con: duckdb.DuckDBPyConnection,
        query: str,
        params: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        result = con.execute(query, params or [])
        description = result.description
        if description is None:
            raise AnalyticsCatalogError("analytics SELECT returned no schema")
        columns = [item[0] for item in description]
        return [
            {
                column: AnalyticsQueryService._json_value(value)
                for column, value in zip(columns, row, strict=True)
            }
            for row in result.fetchall()
        ]

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, date):
            return value.isoformat()
        return value
