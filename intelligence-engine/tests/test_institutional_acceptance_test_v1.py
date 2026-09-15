"""Phase 1 Institutional Acceptance Test — baseline qualification exam."""

from __future__ import annotations

import json
from pathlib import Path

from institutional_evaluation_lab.golden_universe import store as golden_store
from institutional_evaluation_lab.iat.freeze import freeze_baseline
from institutional_evaluation_lab.iat.production import health, run_iat
from institutional_evaluation_lab.iat.schema import REQUIRED_BUCKETS, SCOPE_LOCKS
from knowledge_factory.phase1_golden_test_set import PHASE1_GOLDEN_ROWS


def test_iat_health_scope_locks():
    h = health()
    assert h["acceptance_exam_only"] is True
    assert SCOPE_LOCKS["decision_engine"] == "read_only"
    assert "baseline architecture" in h["question"]


def _bucket_for_index(i: int) -> str:
    # Match REQUIRED_BUCKETS order/sizes
    if i < 50:
        return "nifty_50"
    if i < 100:
        return "nifty_next_50"
    if i < 150:
        return "midcap"
    if i < 175:
        return "smallcap"
    return "special_situation"


def _build_passing_release(tmp_path, monkeypatch, release_id: str = "PR309"):
    root = tmp_path / "results"
    monkeypatch.setenv("IEL_GOLDEN_RESULTS_ROOT", str(root))
    monkeypatch.setenv("IEL_GOLDEN_STORE_ROOT", str(tmp_path / "store"))

    rows = []
    for i, meta in enumerate(PHASE1_GOLDEN_ROWS):
        ticker = meta["ticker"]
        bucket = meta.get("bucket") or _bucket_for_index(i)
        # Mix of decisions — never High Conviction when readiness < 80
        if i % 17 == 0:
            decision, readiness, gate, evidence = "Deferred", 42, "FAIL", "Insufficient"
            failure = {"reason": "SHAREHOLDING_MISSING", "stage": "Ownership Intelligence"}
            pack_present = False
        elif i % 11 == 0:
            decision, readiness, gate, evidence = "Watchlist", 65, "FAIL", "Partial"
            failure = {"reason": "VALUATION_MISSING", "stage": "Valuation Intelligence"}
            pack_present = True
        elif i % 5 == 0:
            decision, readiness, gate, evidence = "High Conviction", 96, "PASS", "Complete"
            failure = None
            pack_present = True
        else:
            decision, readiness, gate, evidence = "Constructive", 88, "PASS", "Complete"
            failure = None
            pack_present = True

        rows.append(
            {
                "ticker": ticker,
                "sector": meta.get("sector") or "Unknown",
                "bucket": bucket,
                "decision": decision,
                "recommendation_readiness": readiness,
                "institutional_readiness": max(readiness - 5, 40),
                "company_quality": 7.2 if gate == "PASS" else 5.5,
                "financial_quality": 7.0,
                "valuation": 6.5,
                "macro": 7.5,
                "technical": 7.0,
                "risk": 6.8,
                "investment_opportunity": 6.8,
                "analytical_confidence": readiness - 1,
                "gate": gate,
                "status": "COMPLETED" if gate == "PASS" else "FAILED",
                "ok": gate == "PASS",
                "evidence_class": evidence,
                "runtime_ms": 1700 + (i % 7) * 50,
                "timing": {"total_ms": 1700 + (i % 7) * 50, "decision_engine_ms": 900},
                "pack_present": pack_present,
                "live_price": True,
                "price_available": True,
                "price_ltp": 100.0 + i,
                "price_source": "groww",
                "price_stale": False,
                "versions": {"constitution_version": "1.4", "decision_engine_version": "ide-v1.0.0"},
                "replay_inputs": {"price_snapshot": {"ltp": 100.0 + i, "source_provider": "groww"}},
                "investment_thesis_status": "INCONCLUSIVE" if gate != "PASS" else "OPEN",
                "failure": failure,
                "release_id": release_id,
                "run_id": f"run-{release_id}",
            }
        )

    assert len(rows) == 200
    counts = {}
    for r in rows:
        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1
    assert counts == REQUIRED_BUCKETS

    summary = {
        "release_id": release_id,
        "run_id": f"run-{release_id}",
        "coverage": {
            "gate_pass_rate_pct": 80.0,
            "average_runtime_ms": 1800,
            "evidence_coverage": {"Complete": 150, "Partial": 30, "Insufficient": 20},
        },
        "health": {"average_runtime_ms": 1800, "average_readiness": 0.85, "gate_pass_rate": 0.8},
        "rows": rows,
        "versions": {"decision_engine_version": "ide-v1.0.0", "constitution_version": "1.4"},
    }
    written = golden_store.save_release_results(summary)
    out_dir = Path(written["results_dir"])

    (out_dir / "_phase6_governance.json").write_text(
        json.dumps(
            {
                "spec_version": "v1.0",
                "critical_rule_failures": 0,
                "governance_assertions": [
                    {"rule_id": f"GOV-00{i}", "status": "PASS", "pass": 200, "fail": 0, "skip": 0}
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
                "current_release": release_id,
                "recommendations_changed": 4,
                "expected": 4,
                "unexpected": 0,
                "by_reason_code": {"DATA": 2, "MODEL": 2, "UNKNOWN": 0},
                "budget": {"passed": True, "breaches": []},
            }
        ),
        encoding="utf-8",
    )
    return out_dir


def test_iat_pass_and_freeze(monkeypatch, tmp_path):
    _build_passing_release(tmp_path, monkeypatch, "PR309")
    pack = run_iat(release_id="PR309", freeze=True, persist=True, require_full_universe=True)
    assert pack["found"] is True
    assert pack["overall"]["status"] == "PASS"
    assert pack["overall"]["qualifies_as_baseline"] is True
    assert pack["governance"]["status"] == "PASS"
    assert pack["evidence"]["status"] == "PASS"
    assert pack["drift"]["status"] == "PASS"
    assert pack["drift"]["unknown_drift"] == 0
    assert pack["universe"]["companies"] == 200
    assert "AGIB Phase 1 qualifies as the production baseline" in pack["report_text"]
    assert pack["freeze"]["frozen"] is True
    assert pack["freeze"]["baseline"]["status"] == "FROZEN"
    assert (Path(pack["results_dir"]) / "_iat_report.md").exists()
    assert (Path(pack["results_dir"]) / "_institutional_baseline_v1_0.md").exists()


def test_iat_refuses_freeze_on_fail(monkeypatch, tmp_path):
    out_dir = _build_passing_release(tmp_path, monkeypatch, "PR309-BAD")
    # Inject unknown drift regression
    (out_dir / "_drift_report.json").write_text(
        json.dumps(
            {
                "recommendations_changed": 10,
                "expected": 4,
                "unexpected": 6,
                "by_reason_code": {"UNKNOWN": 6},
                "budget": {"passed": False, "breaches": ["unknown_drift"]},
            }
        ),
        encoding="utf-8",
    )
    pack = run_iat(release_id="PR309-BAD", freeze=True, persist=True)
    assert pack["overall"]["status"] == "FAIL"
    assert pack["drift"]["status"] == "FAIL"
    assert pack["freeze"]["frozen"] is False
    assert pack["freeze"]["refused"] is True
    assert pack["freeze"]["reason"] == "IAT_DID_NOT_PASS"
    assert "does NOT qualify" in pack["report_text"]


def test_freeze_helper_refuses_without_pass():
    result = freeze_baseline(
        {"overall": {"status": "FAIL"}, "release_id": "X"},
        results_dir=None,
    )
    assert result["frozen"] is False
    assert result["reason"] == "IAT_DID_NOT_PASS"


def test_editorial_violation_fails_governance(monkeypatch, tmp_path):
    out_dir = _build_passing_release(tmp_path, monkeypatch, "PR309-EDIT")
    # Corrupt one row: High Conviction with low readiness
    row_path = out_dir / "RELIANCE.json"
    row = json.loads(row_path.read_text(encoding="utf-8"))
    row["decision"] = "High Conviction"
    row["recommendation_readiness"] = 40
    row["gate"] = "FAIL"
    row_path.write_text(json.dumps(row), encoding="utf-8")
    # Also patch summary rows if loader uses them — load_release_results reads per-ticker files
    pack = run_iat(release_id="PR309-EDIT", freeze=False, persist=False)
    assert pack["governance"]["status"] == "FAIL"
    assert pack["governance"]["editorial_violations"] >= 1
    assert pack["overall"]["status"] == "FAIL"
