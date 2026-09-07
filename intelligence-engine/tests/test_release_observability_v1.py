"""PR #309 — release observability is presentation-only over #306–#308 artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from institutional_evaluation_lab.golden_universe import store as golden_store
from institutional_evaluation_lab.observability.production import build_release_dashboard, health
from institutional_evaluation_lab.observability.schema import SCOPE_LOCKS


def test_scope_locks_presentation_only():
    h = health()
    assert h["presentation_only"] is True
    assert h["governance_programme_status"] == "frozen_after_pr309"
    assert h["post_governance_roadmap"][0] == "earnings_intelligence"
    assert SCOPE_LOCKS["decision_engine"] == "read_only"
    assert SCOPE_LOCKS["governance_spec"] == "read_only"
    assert SCOPE_LOCKS["scoring"] == "read_only"
    assert SCOPE_LOCKS["valuation_models"] == "read_only"
    assert SCOPE_LOCKS["technical_models"] == "read_only"


def test_release_dashboard_consumes_artifacts(monkeypatch, tmp_path):
    root = tmp_path / "results"
    monkeypatch.setenv("IEL_GOLDEN_RESULTS_ROOT", str(root))
    monkeypatch.setenv("IEL_GOLDEN_STORE_ROOT", str(tmp_path / "store"))

    rows = [
        {
            "ticker": "HDFCBANK",
            "sector": "Banking",
            "decision": "Constructive",
            "recommendation_readiness": 95,
            "company_quality": 8.2,
            "financial_quality": 8.8,
            "valuation": 6.5,
            "macro": 8.0,
            "technical": 7.1,
            "gate": "PASS",
            "status": "COMPLETED",
            "evidence_class": "Complete",
            "runtime_ms": 1700,
            "timing": {
                "company_pack_ms": 400,
                "groww_price_ms": 100,
                "decision_engine_ms": 900,
                "company_intelligence_ms": 250,
                "total_ms": 1700,
            },
            "pack_present": True,
            "live_price": True,
            "price_available": True,
        },
        {
            "ticker": "TCS",
            "sector": "IT Services",
            "decision": "High Conviction",
            "recommendation_readiness": 97,
            "company_quality": 8.5,
            "financial_quality": 9.0,
            "valuation": 7.0,
            "macro": 8.0,
            "technical": 7.5,
            "gate": "PASS",
            "status": "COMPLETED",
            "evidence_class": "Complete",
            "runtime_ms": 1500,
            "timing": {
                "company_pack_ms": 350,
                "groww_price_ms": 90,
                "decision_engine_ms": 800,
                "company_intelligence_ms": 200,
                "total_ms": 1500,
            },
            "pack_present": True,
            "live_price": True,
        },
        {
            "ticker": "PAYTM",
            "sector": "Financial Services",
            "decision": "Deferred",
            "recommendation_readiness": 42,
            "company_quality": 6.0,
            "financial_quality": 3.0,
            "valuation": None,
            "macro": 7.0,
            "technical": 5.0,
            "gate": "FAIL",
            "status": "FAILED",
            "evidence_class": "Insufficient",
            "failure": {"reason": "SHAREHOLDING_MISSING", "stage": "Ownership Intelligence"},
            "runtime_ms": 2000,
            "timing": {
                "company_pack_ms": 500,
                "groww_price_ms": 120,
                "decision_engine_ms": 1100,
                "company_intelligence_ms": 280,
                "total_ms": 2000,
            },
            "pack_present": False,
        },
    ]
    summary = {
        "release_id": "PR309",
        "run_id": "run-PR309",
        "coverage": {
            "gate_pass_rate_pct": 66.7,
            "average_runtime_ms": 1733,
            "evidence_coverage": {"Complete": 2, "Partial": 0, "Insufficient": 1},
        },
        "health": {"average_runtime_ms": 1733, "average_readiness": 0.78, "gate_pass_rate": 0.667},
        "rows": rows,
        "versions": {"decision_engine_version": "ide-v1.0.0", "runner_version": "1.0.0"},
    }
    written = golden_store.save_release_results(summary)
    out_dir = Path(written["results_dir"])

    # Phase 6 + drift artifacts (produced by #307/#308 — consumed, not recomputed)
    (out_dir / "_phase6_governance.json").write_text(
        json.dumps(
            {
                "spec_version": "v1.0",
                "critical_rule_failures": 0,
                "governance_assertions": [
                    {"rule_id": f"GOV-00{i}", "status": "PASS", "pass": 3, "fail": 0, "skip": 0}
                    for i in range(1, 9)
                ],
            }
        ),
        encoding="utf-8",
    )
    (out_dir / "_drift_report.json").write_text(
        json.dumps(
            {
                "previous_release": "PR308",
                "current_release": "PR309",
                "recommendations_changed": 4,
                "expected": 4,
                "unexpected": 0,
                "by_reason_code": {"DATA": 2, "MODEL": 2, "UNKNOWN": 0, "NONE": 196},
                "budget": {"passed": True, "breaches": []},
                "review_queue": {"requires_review": 0},
            }
        ),
        encoding="utf-8",
    )

    pack = build_release_dashboard("PR309", persist=True)
    assert pack["found"] is True
    assert pack["presentation_only"] is True
    exe = pack["executive"]
    assert exe["release"] == "PR309"
    assert exe["status"] == "PASS"
    assert exe["companies_tested"] == 3
    assert exe["governance_pct"] == 100.0
    assert exe["unknown_drift"] == 0

    dist = pack["recommendation_distribution"]["distribution"]
    assert dist["Constructive"] == 1
    assert dist["High Conviction"] == 1
    assert dist["Deferred"] == 1

    gov = pack["governance"]
    assert gov["present"] is True
    assert gov["overall_pct"] == 100.0
    assert gov["rules"][0]["rule_id"] == "GOV-001"

    drift = pack["drift"]
    assert drift["present"] is True
    assert drift["recommendation_changes"] == 4
    assert drift["budget"] == "PASS"

    perf = pack["performance"]
    assert perf["slowest_module"] == "Decision Engine"
    assert perf["average_runtime_s"] is not None

    cov = pack["coverage"]
    assert cov["financials_pct"] is not None
    assert "Ownership" not in cov  # keys are *_pct
    assert cov["ownership_pct"] >= 0

    assert "Executive Release Dashboard" in pack["text"]
    assert Path(pack["dashboard_path"]).exists()
    assert Path(pack["markdown_path"]).exists()
