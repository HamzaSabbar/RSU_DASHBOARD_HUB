from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from data_platform.cache import VersionedResultCache
from data_platform.pipeline import RsuCsvPipeline
from data_platform.query import AnalyticsQueryService, cache_key
from data_platform.schemas import AnalyticsFilters


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_versioned_result_cache_is_bounded_and_release_scoped() -> None:
    cache = VersionedResultCache(ttl_seconds=60, max_entries=2, max_bytes=1024)
    key_v1 = cache_key("release-1", "dashboard", {"subject": "ASD"})
    key_v2 = cache_key("release-2", "dashboard", {"subject": "ASD"})
    cache.set(key_v1, {"value": 1})

    assert cache.get(key_v1) == {"value": 1}
    assert cache.get(key_v2) is None

    cache.set("second", {"value": 2})
    cache.set("third", {"value": 3})
    assert cache.get(key_v1) is None
    assert cache.stats().entries == 2
    assert cache.stats().evictions == 1


def test_result_cache_expires_entries() -> None:
    cache = VersionedResultCache(ttl_seconds=1, max_entries=4, max_bytes=1024)
    cache.set("key", {"value": 1})
    # Avoid a one-second test sleep by moving the private deadline in a focused unit test.
    cache._items["key"].expires_at = time.monotonic() - 1  # noqa: SLF001
    assert cache.get("key") is None


def test_csv_pipeline_builds_queryable_release(tmp_path: Path) -> None:
    source = tmp_path / "raw"
    analytics = tmp_path / "analytics"
    _write(
        source / "menage.csv",
        "menage_ano,milieu,region_id,region,province_id,province,commune_id,commune,type_menage,taille_menage,etat_matrimonial_cm,genre_cm,sexe_id,date_naissance_cm\n"
        "1,Urbain,4,Rabat-Salé-Kénitra,17,RABAT,1655,RABAT,individuel,1,Célibataire,Masculin,1,1990-01-01\n"
        "2,Rural,6,Casablanca-Settat,21,CASABLANCA,2000,CASABLANCA,couple,3,Marié,Féminin,2,1985-01-01\n",
    )
    _write(
        source / "score.csv",
        "menage_ano,score_id_ano,type_demande,score_corrige,score_calcule,date_calcul\n"
        "1,101,Inscription,10.0,10.0,2024-03-05 10:00:00.000000\n"
        "1,102,Mise à jour,9.0,9.0,2024-04-10 10:00:00.000000\n"
        "2,201,Inscription,9.0,9.0,2024-03-05 10:00:00.000000\n"
        "2,202,Mise à jour,10.0,10.0,2024-04-10 10:00:00.000000\n",
    )
    _write(
        source / "beneficiaire.csv",
        "menage_ano,partner_id,motif,date_insert,actif\n"
        "1,asd,1,2024-04-10 10:00:00.000000,True\n",
    )
    _write(source / "asd.csv", "menage_ano\n1\n")
    _write(source / "amot.csv", "menage_ano\n2\n")
    _write(source / "amoa.csv", "menage_ano\n")
    _write(source / "ref_motif_beneficiaire.csv", "motif,\n1,forfait\n")
    _write(source / "ref_variable.csv", "variable_id,name,,,\n88,Logement secondaire,,,\n")
    _write(
        source / "score_variable.csv",
        "score_id_ano,menage_ano,variable_id,score_variable_coeficient,score_variable_valeur_calcule,score_variable_valeur_corrige\n"
        "101,1,88,0.1,0.1,\n",
    )
    _write(
        source / "parameters" / "rsu_parameters.json",
        json.dumps(
            {
                "program_thresholds": [
                    {"program": "ASD", "threshold": 9.743001},
                    {"program": "AMOT", "threshold": 9.3264284},
                    {"program": "AMOA", "threshold": 1000.0},
                ],
                "tuning": {},
            }
        ),
    )

    result = RsuCsvPipeline(
        source_path=source,
        analytics_path=analytics,
        pipeline_version="test-v1",
        memory_limit="512MB",
        threads=1,
        temp_directory=analytics / "tmp",
        max_temp_directory_size="1GB",
        include_score_variables=True,
    ).build("12345678-0000-0000-0000-000000000000")

    assert result.database_path.is_file()
    assert result.manifest_path.is_file()
    assert result.row_counts["fact_score_event"] == 4
    assert result.row_counts["fact_program_crossing"] == 2
    assert any(item["format"] == "arrow" for item in result.artifacts)

    service = AnalyticsQueryService(result.database_path, threads=1)
    options = service.filter_options(result.version_key)
    assert options["period_start"] == date(2024, 3, 5)
    dashboard = service.social_programs_dashboard(
        result.version_key,
        AnalyticsFilters(
            subject="ALL",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 4, 30),
            granularity="month",
        ),
    )
    assert dashboard["summary"]["eligible_households"] == 1
    totals = {item["program_code"]: item for item in dashboard["summary"]["programs"]}
    assert totals["ASD"]["entries"] == 1
    assert totals["AMOT"]["exits"] == 1
