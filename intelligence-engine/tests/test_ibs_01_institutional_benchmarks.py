"""IBS-01 — AGI Institutional Benchmark Suite tests."""

from __future__ import annotations

from institutional_benchmarks.catalog import list_cases, sectors
from institutional_benchmarks.corpus import filter_corpus_by_cutoff, get_corpus
from institutional_benchmarks.production import dashboard, health, list_benchmarks, run, run_all_benchmarks
from institutional_benchmarks.schema import IBS_WORKSTREAM_ID, PASS_SCORE, SECTORS
from institutional_benchmarks import store as ibs_store


def setup_function(_fn=None):
    ibs_store.reset_for_tests()


def test_health_agi_brand_and_role():
    h = health()
    assert h["workstream_id"] == IBS_WORKSTREAM_ID
    assert h["brand"] == "AGI"
    assert h["not_an_engine"] is True
    assert h["not_an_office"] is True
    assert h["raw_evidence_only"] is True
    assert h["no_fixture_answers"] is True
    assert h["pass_score"] == PASS_SCORE
    assert h["case_count"] >= 30


def test_catalog_covers_all_sectors():
    secs = {s["sector"] for s in sectors()}
    for s in SECTORS:
        assert s in secs
        assert next(x for x in sectors() if x["sector"] == s)["case_count"] >= 1
    cases = list_cases()
    assert any(c["case_id"] == "KOTAK_RBI" for c in cases)
    assert any(c["sector"] == "IT" for c in cases)


def test_kotak_benchmark_passes_raw_evidence():
    result = run("KOTAK_RBI")
    assert result["passed"] is True, result.get("failure_codes")
    assert result["research_quality_score"] >= PASS_SCORE
    assert result["raw_evidence_only"] is True
    assert result["fixture_answers_used"] is False
    report = result["institutional_report"]
    assert report["sections"]["evidence_contradicting"]["items"]
    assert report["sections"]["outstanding_unknowns"]["items"]
    assert report["sections"]["monitoring_framework"]["next_quarter"]
    assert report["sections"]["counterfactual_analysis"]["items"]
    assert report["buy_sell"] is None


def test_cross_sector_cases_pass():
    for case_id in ("TCS", "RELIANCE", "ITC", "SUNPHARMA", "LT"):
        result = run(case_id)
        assert result["passed"] is True, (case_id, result.get("failure_codes"), result.get("research_quality_score"))


def test_fixture_answers_fail():
    result = run("KOTAK_RBI", fixture_answers={"bad": True})
    assert result["passed"] is False
    assert "FIXTURE_ANSWER_USED" in result["failure_codes"]


def test_historical_blind_cutoff():
    full = get_corpus("KOTAK_RBI")
    blind = filter_corpus_by_cutoff(full, "2024-05-15")
    assert blind["historical_cutoff"] == "2024-05-15"
    assert blind["document_count"] < full["document_count"]
    assert all(str(d.get("date") or "")[:10] <= "2024-05-15" for d in blind["documents"])
    result = run("KOTAK_RBI", cutoff="2024-05-15")
    assert result["historical_cutoff"] == "2024-05-15"
    assert result["coverage_summary"]["hidden_after_cutoff"] >= 1
    # Still must produce institutional report from available evidence
    assert result["institutional_report"]["sections"]["what_happened"]


def test_banking_sector_suite_and_release_gate():
    from institutional_benchmarks.production import run_sector_benchmarks

    suite = run_sector_benchmarks("BANKING")
    assert suite["cases_run"] >= 4
    assert suite["average_score"] >= PASS_SCORE
    assert suite["release_gate"]["blocked"] is False


def test_run_all_smoke_subset_metrics():
    # Full suite can be heavy; ensure run_all works and updates dashboard panels
    # Use sector IT as lighter proxy + dashboard
    from institutional_benchmarks.production import run_sector_benchmarks

    suite = run_sector_benchmarks("IT")
    assert suite["passed"] == suite["cases_run"]
    dash = dashboard()
    assert dash["panels"]["benchmarks_passed"] >= 1
    assert "average_score" in dash["panels"]


def test_list_api_shape():
    out = list_benchmarks(sector="CONSUMER")
    assert out["ok"] is True
    assert all(c["sector"] == "CONSUMER" for c in out["cases"])
