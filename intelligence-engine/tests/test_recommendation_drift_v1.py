"""PR #308 — controlled recommendation drift with reason codes + budget."""

from __future__ import annotations

import json
from pathlib import Path

from institutional_evaluation_lab.drift.budget import evaluate_budget
from institutional_evaluation_lab.drift.classify import classify_reason
from institutional_evaluation_lab.drift.magnitude import compute_magnitude
from institutional_evaluation_lab.drift.production import compare_releases
from institutional_evaluation_lab.drift.release_notes import format_release_notes
from institutional_evaluation_lab.golden_universe import store as golden_store


def test_classify_data_vs_unknown():
    prev = {
        "decision": "Deferred",
        "evidence_class": "Insufficient",
        "recommendation_readiness": 40,
        "gate": "FAIL",
        "pack_present": False,
    }
    cur_data = {
        "decision": "Constructive",
        "evidence_class": "Complete",
        "recommendation_readiness": 92,
        "gate": "PASS",
        "pack_present": True,
    }
    assert classify_reason(prev, cur_data)["code"] == "DATA"

    cur_unknown = {
        "decision": "Constructive",
        "evidence_class": "Insufficient",
        "recommendation_readiness": 41,
        "gate": "FAIL",
        "pack_present": False,
        "valuation": 6.0,
        "price_ltp": 100.0,
        "versions": {"decision_engine_version": "ide-v1.0.0"},
    }
    prev2 = {
        **prev,
        "valuation": 6.0,
        "price_ltp": 100.0,
        "versions": {"decision_engine_version": "ide-v1.0.0"},
    }
    assert classify_reason(prev2, cur_unknown)["code"] == "UNKNOWN"


def test_classify_model_and_market():
    prev = {
        "decision": "Constructive",
        "evidence_class": "Complete",
        "recommendation_readiness": 94,
        "gate": "PASS",
        "valuation": 6.8,
        "price_ltp": 1000.0,
        "versions": {"decision_engine_version": "ide-v1.0.0", "runner_version": "1.0.0"},
    }
    cur_model = {
        **prev,
        "decision": "Neutral",
        "versions": {"decision_engine_version": "ide-v2.1.0", "runner_version": "1.0.0"},
    }
    assert classify_reason(prev, cur_model)["code"] == "MODEL"

    cur_market = {
        **prev,
        "decision": "Neutral",
        "valuation": 5.5,
        "price_ltp": 900.0,
        "versions": prev["versions"],
    }
    assert classify_reason(prev, cur_market)["code"] == "MARKET"


def test_magnitude_and_budget():
    prev = {
        "company_quality": 8.3,
        "financial_quality": 8.0,
        "valuation": 6.8,
        "recommendation_readiness": 96,
        "decision": "Constructive",
    }
    cur = {
        "company_quality": 8.4,
        "financial_quality": 8.1,
        "valuation": 6.2,
        "recommendation_readiness": 96,
        "decision": "Constructive",
    }
    mag = compute_magnitude(prev, cur)
    assert mag["decision"]["changed"] is False
    assert mag["by_field"]["valuation"]["delta"] == -0.6

    budget_ok = evaluate_budget(
        n=200,
        recommendation_changes=7,
        unknown_count=0,
        governance_failures=0,
        prev_avg_runtime_ms=1800,
        cur_avg_runtime_ms=1820,
        prev_avg_readiness=91,
        cur_avg_readiness=91.5,
    )
    assert budget_ok["passed"] is True

    budget_fail = evaluate_budget(
        n=200,
        recommendation_changes=20,
        unknown_count=2,
        governance_failures=1,
        prev_avg_runtime_ms=1800,
        cur_avg_runtime_ms=2200,
        prev_avg_readiness=91,
        cur_avg_readiness=96,
        data_driven_readiness_shift=False,
    )
    assert budget_fail["passed"] is False
    metrics = {b["metric"] for b in budget_fail["breaches"]}
    assert "unknown_drift" in metrics
    assert "recommendation_changes" in metrics


def _write_release(root: Path, release_id: str, rows: list[dict]) -> None:
    import os

    os.environ["IEL_GOLDEN_RESULTS_ROOT"] = str(root)
    # Default summary versions; per-row versions (e.g. IDE bump) must win on save.
    default_ide = "ide-v1.0.0"
    if rows and isinstance(rows[0].get("versions"), dict):
        # Use first row only as fallback default — row-level stamps still override in payload
        default_ide = rows[0]["versions"].get("decision_engine_version") or default_ide
    out = {
        "release_id": release_id,
        "run_id": f"run-{release_id}",
        "commit": "abc1234",
        "suite": "phase1_golden_200",
        "version": "iel-golden-eval-v1.0.0",
        "coverage": {"gate_pass_rate_pct": 93.0, "average_runtime_ms": 1820},
        "health": {"average_runtime_ms": 1820, "gate_pass_rate": 0.93},
        "rows": rows,
        "versions": {
            "constitution_version": "v1.4",
            "decision_engine_version": default_ide,
            "runner_version": "1.0.0",
            "golden_universe_version": "v1.0",
        },
    }
    golden_store.save_release_results(out)


def test_compare_releases_end_to_end(monkeypatch, tmp_path):
    root = tmp_path / "results"
    monkeypatch.setenv("IEL_GOLDEN_RESULTS_ROOT", str(root))
    monkeypatch.setenv("IEL_GOLDEN_STORE_ROOT", str(tmp_path / "store"))

    prev_rows = [
        {
            "ticker": "HDFCBANK",
            "sector": "Banking",
            "decision": "Constructive",
            "recommendation_readiness": 96,
            "company_quality": 8.3,
            "financial_quality": 8.0,
            "valuation": 6.8,
            "evidence_class": "Complete",
            "gate": "PASS",
            "runtime_ms": 1800,
            "price_ltp": 1600,
            "versions": {"decision_engine_version": "ide-v1.0.0", "runner_version": "1.0.0"},
        },
        {
            "ticker": "PAYTM",
            "sector": "Financial Services",
            "decision": "Deferred",
            "recommendation_readiness": 40,
            "company_quality": 6.0,
            "financial_quality": 4.0,
            "valuation": 5.0,
            "evidence_class": "Insufficient",
            "gate": "FAIL",
            "runtime_ms": 1700,
            "pack_present": False,
            "versions": {"decision_engine_version": "ide-v1.0.0", "runner_version": "1.0.0"},
        },
        {
            "ticker": "TCS",
            "sector": "IT Services",
            "decision": "Constructive",
            "recommendation_readiness": 94,
            "company_quality": 8.5,
            "financial_quality": 8.8,
            "valuation": 7.0,
            "evidence_class": "Complete",
            "gate": "PASS",
            "runtime_ms": 1750,
            "price_ltp": 4000,
            "versions": {"decision_engine_version": "ide-v1.0.0", "runner_version": "1.0.0"},
        },
    ]
    cur_rows = [
        {
            **prev_rows[0],
            "decision": "Neutral",
            # Keep valuation/price stable so classifier attributes the flip to MODEL
            "versions": {"decision_engine_version": "ide-v2.1.0", "runner_version": "1.0.0"},
        },
        {
            **prev_rows[1],
            "decision": "Constructive",
            "recommendation_readiness": 88,
            "evidence_class": "Complete",
            "gate": "PASS",
            "pack_present": True,
            "financial_quality": 7.5,
        },
        dict(prev_rows[2]),
    ]

    _write_release(root, "PR306", prev_rows)
    _write_release(root, "PR308", cur_rows)

    report = compare_releases(
        previous_release="PR306",
        current_release="PR308",
        governance_failures=0,
        persist=True,
    )
    assert report["n"] == 3
    assert report["recommendations_changed"] == 2
    by_ticker = {r["ticker"]: r for r in report["rows"]}
    assert by_ticker["HDFCBANK"]["reason_code"] == "MODEL"
    assert "IDE" in by_ticker["HDFCBANK"]["reason"]["detail"]
    assert by_ticker["PAYTM"]["reason_code"] == "DATA"
    assert by_ticker["TCS"]["reason_code"] == "NONE"
    assert by_ticker["HDFCBANK"]["magnitude"]["by_field"]["valuation"]["delta"] == 0.0

    notes = report["release_notes"]
    assert notes["recommendations_changed"] == 2
    assert notes["expected"] == 2
    assert notes["unexpected"] == 0
    text = format_release_notes(notes)
    assert "Release PR308" in text

    assert Path(report["report_path"]).exists()
    disk = json.loads(Path(report["report_path"]).read_text())
    assert disk["by_reason_code"]["MODEL"] == 1
    assert disk["by_reason_code"]["DATA"] == 1

    # UNKNOWN should fail release
    bad_cur = [
        {
            **prev_rows[0],
            "decision": "Watchlist",
            # no material signal
        },
        dict(prev_rows[1]),
        dict(prev_rows[2]),
    ]
    _write_release(root, "PR308b", bad_cur)
    bad = compare_releases(
        previous_release="PR306",
        current_release="PR308b",
        governance_failures=0,
        persist=False,
    )
    assert bad["unexpected"] >= 1
    assert bad["ok"] is False
    assert bad["review_queue"]["requires_review"] >= 1
