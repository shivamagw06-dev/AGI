"""FSE-04.3 — Production Certification Corpus & Golden Dataset tests."""

from __future__ import annotations

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.parsing.pcc.corpus import corpus_health, list_cases, load_case
from financial_statements_engine.parsing.pcc.freeze import freeze_candidate, promote_forbidden_guard
from financial_statements_engine.parsing.pcc.history import list_certifications, load_certification
from financial_statements_engine.parsing.pcc.production import dashboard, health, run_certification
from financial_statements_engine.parsing.pcc.schema import PCC_GATES, WORKSTREAM_ID
from financial_statements_engine.parsing.production import parse_bytes


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def test_pcc_health_and_corpus(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["read_only_golden"] is True
    assert h["auto_promote_forbidden"] is True
    assert "production_certification_corpus" in h["capabilities"]
    ch = corpus_health()
    assert ch["case_count"] >= 10
    assert "information_technology" in ch["cases_by_sector"]
    assert "banking" in ch["cases_by_sector"]
    cases = list_cases()
    assert all(c["immutable"] for c in cases)


def test_load_case_has_expected_artifacts(fse_tmp):
    case = load_case("information_technology", "tcs_fy2025_annual")
    assert case["metadata"]["ticker"] == "TCS"
    assert case["immutable"] is True
    assert case["expected"]["metrics"]["expected_metrics"]
    assert case["expected"]["validation"]["status"] == "deferred"
    assert case["raw_bytes"]


def test_corpus_certification_passes(fse_tmp):
    report = run_certification()
    assert report["documents_processed"] >= 10
    assert report["immutable"] is True
    assert report["golden_dataset_mutated"] is False
    assert report["passed"] is True
    assert report["production_eligible"] is True
    assert report["deployment_recommendation"] == "deploy"
    assert not report["failed_cases"]
    # permanently stored
    stored = load_certification(report["certification_id"])
    assert stored is not None
    assert stored["certification_id"] == report["certification_id"]
    assert len(list_certifications()) >= 1
    events = {e["event_type"] for e in get_bus().tail(200)}
    assert "pcc.certification.started.v1" in events
    assert "pcc.certification.completed.v1" in events


def test_sector_filter_certification(fse_tmp):
    report = run_certification(sector="information_technology")
    assert report["passed"] is True
    assert report["documents_processed"] == 2
    assert all(r["sector"] == "information_technology" for r in report["case_results"])


def test_gates_thresholds_present(fse_tmp):
    assert PCC_GATES["parse_manifest_match_pct"] == 100.0
    assert PCC_GATES["metric_mapping_accuracy_pct"] == 99.5
    assert PCC_GATES["unknown_label_rate_pct_max"] == 0.5


def test_freeze_never_auto_promotes(fse_tmp):
    case = load_case("information_technology", "tcs_fy2025_annual")
    import json

    data = json.dumps((case["raw"] or {}).get("document") or case["raw"], sort_keys=True).encode("utf-8")
    result = parse_bytes(
        "TCS",
        data,
        document_type="json",
        period_end="2025-03-31",
        period_type="annual",
        evidence_id="pcc:freeze:tcs",
    )
    frozen = freeze_candidate("information_technology", "tcs_fy2025_annual", result)
    assert frozen["promoted_to_expected"] is False
    assert promote_forbidden_guard()["forbidden"] is True
    # golden expected untouched
    reloaded = load_case("information_technology", "tcs_fy2025_annual")
    assert reloaded["expected"]["metrics"]["expected_metrics"] == case["expected"]["metrics"]["expected_metrics"]


def test_dashboard(fse_tmp):
    run_certification(sector="banking")
    dash = dashboard()
    assert dash["golden_dataset_health"]["case_count"] >= 10
    assert dash["certification_dashboard"]["latest"] is not None
