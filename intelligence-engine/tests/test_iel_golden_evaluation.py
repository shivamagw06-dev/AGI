"""IEL Golden Universe Evaluation Runner — metrics, QA, drift, dashboards."""

from __future__ import annotations

from institutional_evaluation_lab.golden_universe.dashboards import coverage_dashboard, sector_dashboard
from institutional_evaluation_lab.golden_universe.metrics import extract_metrics
from institutional_evaluation_lab.golden_universe.qa_governance import run_qa_checks
from institutional_evaluation_lab.golden_universe.recommendation_drift import (
    compare_recommendation_drift,
)
from institutional_evaluation_lab.golden_universe.runner import run_golden_evaluation
from institutional_evaluation_lab.golden_universe.scorecard import release_scorecard
from institutional_evaluation_lab.production import golden_evaluation_health, status


def _fake_price(ticker: str, force: bool = False) -> dict:
    return {
        "refreshed": True,
        "age_sec": 5,
        "snapshot": {
            "ltp": 1000.0,
            "stale": False,
            "source_provider": "groww",
            "as_of": "2026-07-29T10:00:00Z",
        },
        "provider_called": "groww",
    }


def _fake_ide(
    ticker: str,
    *,
    query: str = "",
    cid=None,
    company_analysis=None,
    live_evidence=None,
) -> dict:
    # Thin but coherent IDE package for tests
    readiness = 94.0 if ticker in {"HDFCBANK", "TCS", "INFY"} else 55.0
    gate_status = "PASSED" if readiness >= 80 else "FAILED"
    band = "high_conviction_allowed" if readiness >= 90 else ("deferred" if readiness < 60 else "watchlist")
    thesis = "FORMED" if readiness >= 80 else "INCONCLUSIVE"
    decision = "Constructive" if readiness >= 90 else ("Deferred" if readiness < 60 else "Watchlist")
    return {
        "enabled": True,
        "active": True,
        "ticker": ticker,
        "company_name": ticker,
        "overall_score": 78 if readiness >= 80 else None,
        "investment_grade": "A-" if readiness >= 80 else None,
        "layers": [
            {"id": "macro", "score": 80},
            {"id": "company_quality", "score": 82},
            {"id": "financial_quality", "score": 88, "evidence_quality_score": 88},
            {"id": "valuation", "score": 65},
            {"id": "technical", "score": 71},
            {"id": "risk", "score": 78},
            {"id": "decision", "action": decision.lower(), "investment_thesis_status": thesis},
        ],
        "institutional_readiness_gate": {
            "status": gate_status,
            "band": band,
            "evidence_confidence_pct": readiness,
            "overall_coverage_pct": readiness,
            "investment_thesis_status": thesis,
            "not_a_negative_view": thesis == "INCONCLUSIVE",
            "company_quality_10": 8.2,
            "hard_fail": gate_status == "FAILED",
        },
        "summary": {
            "action": decision.lower(),
            "evidence_confidence_pct": readiness,
            "overall_coverage_pct": readiness,
            "readiness_band": band,
            "investment_thesis_status": thesis,
            "company_quality_10": 8.2,
            "gate_blocked": gate_status == "FAILED",
            "overall_score": 78 if readiness >= 80 else None,
        },
        "decision": {"action": decision.lower(), "investment_thesis_status": thesis},
    }


def test_extract_metrics_shape():
    ide = _fake_ide("HDFCBANK")
    price = _fake_price("HDFCBANK")
    row = extract_metrics(
        ticker="HDFCBANK",
        company_name="HDFC Bank",
        sector="Banking",
        bucket="nifty_50",
        ide_pkg=ide,
        price_pkg=price,
        pack_present=True,
        runtime_ms=2150,
    )
    assert row["ticker"] == "HDFCBANK"
    assert row["company_quality"] == 8.2
    assert row["financial_quality"] == 8.8
    assert row["valuation"] == 6.5
    assert row["recommendation_readiness"] == 94.0
    assert row["live_price"] is True
    assert row["gate"] == "PASS"
    assert row["decision"] in {"Constructive", "High Conviction"}


def test_structured_failure_shareholding_missing():
    from institutional_evaluation_lab.golden_universe.failures import classify_failure

    fail = classify_failure(
        pack_present=True,
        price_pkg={"snapshot": {"ltp": 100}},
        cid={},
        company_analysis={},
        ide_pkg={
            "institutional_readiness_gate": {
                "status": "FAILED",
                "missing": ["Shareholding"],
                "diagnostic_cards": [
                    {"key": "ownership", "present": False, "label": "Current shareholding"}
                ],
            }
        },
        metrics={"gate": "FAIL"},
        errors=[],
    )
    assert fail is not None
    assert fail["reason"] == "SHAREHOLDING_MISSING"
    assert fail["stage"] == "Ownership Intelligence"
    assert fail["retryable"] is True


def test_qa_blocks_high_conviction_on_low_readiness():
    bad = {
        "ticker": "PAYTM",
        "decision": "High Conviction",
        "readiness_band": "high_conviction_allowed",
        "recommendation_readiness": 40,
        "price_available": True,
        "gate": "FAIL",
        "investment_thesis_status": "FORMED",
        "company_quality": 9.5,
        "financial_quality": 9.5,
        "overall_score": 3.0,
        "valuation": 2.0,
        "not_a_negative_view": False,
    }
    qa = run_qa_checks(bad)
    assert qa["passed"] is False
    rules = {v["rule"] for v in qa["violations"]}
    assert "no_high_conviction_below_readiness_floor" in rules
    assert "inconclusive_required_when_evidence_missing" in rules
    assert "quality_vs_overall_inconsistency" in rules
    assert "weak_valuation_high_conviction_needs_justification" in rules


def test_recommendation_drift_classifies_unexpected():
    prev = [
        {
            "ticker": "HDFCBANK",
            "decision": "Neutral",
            "recommendation_readiness": 92,
            "evidence_class": "Complete",
            "gate": "PASS",
        },
        {
            "ticker": "PAYTM",
            "decision": "Deferred",
            "recommendation_readiness": 40,
            "evidence_class": "Insufficient",
            "gate": "FAIL",
        },
    ]
    cur = [
        {
            "ticker": "HDFCBANK",
            "decision": "Constructive",
            "recommendation_readiness": 92,
            "evidence_class": "Complete",
            "gate": "PASS",
        },
        {
            "ticker": "PAYTM",
            "decision": "Deferred",
            "recommendation_readiness": 40,
            "evidence_class": "Insufficient",
            "gate": "FAIL",
        },
    ]
    drift = compare_recommendation_drift(
        cur, prev, previous_label="PR304", current_label="PR305"
    )
    assert drift["changed"] == 1
    hdfc = next(r for r in drift["rows"] if r["ticker"] == "HDFCBANK")
    assert hdfc["class"] == "unexpected_possible_regression"
    paytm = next(r for r in drift["rows"] if r["ticker"] == "PAYTM")
    assert paytm["class"] == "no_change"


def test_coverage_and_sector_dashboards():
    rows = [
        {
            "ticker": "HDFCBANK",
            "sector": "Banking",
            "evidence_class": "Complete",
            "recommendation_readiness": 96,
            "runtime_ms": 2100,
            "gate": "PASS",
            "live_price": True,
            "qa_passed": True,
        },
        {
            "ticker": "TCS",
            "sector": "IT Services",
            "evidence_class": "Complete",
            "recommendation_readiness": 94,
            "runtime_ms": 2000,
            "gate": "PASS",
            "live_price": True,
            "qa_passed": True,
        },
        {
            "ticker": "PAYTM",
            "sector": "Financial Services",
            "evidence_class": "Insufficient",
            "recommendation_readiness": 40,
            "runtime_ms": 1800,
            "gate": "FAIL",
            "live_price": True,
            "qa_passed": False,
        },
    ]
    cov = coverage_dashboard(rows)
    assert cov["companies"] == 3
    assert cov["evidence_coverage"]["Complete"] == 2
    assert cov["gate_pass_rate_pct"] == 66.7
    sec = sector_dashboard(rows)
    assert sec["sector_count"] == 3


def test_run_golden_evaluation_smoke(monkeypatch, tmp_path):
    monkeypatch.setenv("IEL_GOLDEN_STORE_ROOT", str(tmp_path / "golden"))
    monkeypatch.setenv("IEL_GOLDEN_RESULTS_ROOT", str(tmp_path / "results"))
    out = run_golden_evaluation(
        limit=5,
        persist=True,
        persist_baseline=True,
        compare_previous=False,
        release_id="PR306",
        ide_runner=_fake_ide,
        price_runner=_fake_price,
    )
    assert out["kind"] == "golden_universe_evaluation"
    assert out["n"] == 5
    assert out["coverage"]["companies"] == 5
    assert out["scorecard"]["health"] in {"green", "amber", "red"}
    assert out["qa"]["n"] == 5
    assert len(out["rows"]) == 5
    assert out["rows"][0]["pipeline"]["decision_engine"] is True

    # Primary PR #306 artifact: results/PR306/{TICKER}.json
    import json
    from pathlib import Path

    from institutional_evaluation_lab.golden_universe import store as golden_store
    from institutional_evaluation_lab.replay.engine import replay_ticker

    results = out["results"]
    results_dir = Path(results["results_dir"])
    assert results_dir.name == "PR306"
    assert (results_dir / "_manifest.json").exists()
    assert (results_dir / "_summary.json").exists()
    manifest = json.loads((results_dir / "_manifest.json").read_text())
    assert manifest["release_id"] == "PR306"
    assert manifest["timestamp"]
    assert manifest["git_commit"] or manifest["git_commit"] is None
    assert manifest["constitution_version"] == "v1.4"
    assert manifest["decision_engine_version"]
    assert manifest["golden_universe_version"] == "v1.0"
    assert manifest["runner_version"] == "1.0.0"
    assert "health" in manifest
    summary_disk = json.loads((results_dir / "_summary.json").read_text())
    assert summary_disk["companies"] == 5
    assert "completed" in summary_disk
    assert "average_runtime_ms" in summary_disk
    assert "gate_pass_rate" in summary_disk

    ticker_files = sorted(p.name for p in results_dir.glob("*.json") if not p.name.startswith("_"))
    assert len(ticker_files) == 5
    sample = ticker_files[0]
    payload = json.loads((results_dir / sample).read_text())
    assert payload["ticker"] == sample.replace(".json", "")
    assert "recommendation_readiness" in payload
    assert "decision" in payload
    assert "runtime_ms" in payload
    assert "timing" in payload
    assert "company_pack_ms" in payload["timing"]
    assert "groww_price_ms" in payload["timing"]
    assert "decision_engine_ms" in payload["timing"]
    assert "total_ms" in payload["timing"]
    assert "gate" in payload
    assert payload.get("status") in {"COMPLETED", "FAILED"}
    if payload["status"] == "FAILED":
        assert payload.get("failure", {}).get("reason")
    loaded = golden_store.load_release_results("PR306")
    assert loaded is not None
    assert loaded["n"] == 5

    # Deterministic replay with stored price snapshot + same IDE stub
    replay = replay_ticker(
        release_id="PR306",
        ticker=payload["ticker"],
        ide_runner=_fake_ide,
    )
    assert replay["ok"] is True
    assert replay["regression"] is False

    # Second run vs baseline → drift report
    out2 = run_golden_evaluation(
        limit=5,
        persist=True,
        persist_baseline=False,
        compare_previous=True,
        release_id="PR306-test-2",
        previous_label="PR306",
        current_label="PR306-test-2",
        ide_runner=_fake_ide,
        price_runner=_fake_price,
    )
    assert "by_class" in out2["drift"]
    card = release_scorecard(out2)
    assert card["companies"] == 5
    assert Path(out2["results"]["results_dir"]).name == "PR306-test-2"


def test_production_health_exposes_golden():
    st = status()
    assert st["version"].startswith("institutional-evaluation-lab-v1.1")
    assert "golden_universe_evaluation" in st
    gh = golden_evaluation_health()
    assert gh["suite"] == "phase1_golden_200"
    assert gh["universe"]["n"] == 200
