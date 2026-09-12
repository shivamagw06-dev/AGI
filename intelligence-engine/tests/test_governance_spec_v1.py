"""Governance Spec v1.0 + Phase 6 assertions over Evaluation Lab JSON."""

from __future__ import annotations

import json
from pathlib import Path

from governance_spec.assertions import assert_ticker
from governance_spec.phase6 import format_board, run_phase6
from governance_spec.v1_0.rules import FROZEN_RULE_IDS, evaluate_rule, spec_board
from institutional_evaluation_lab.golden_universe.runner import run_golden_evaluation


def test_spec_v1_frozen_catalogue():
    board = spec_board()
    assert board["spec_version"] == "v1.0"
    assert board["frozen"] is True
    assert board["rule_ids"] == list(FROZEN_RULE_IDS)
    assert len(board["rules"]) == 8
    assert board["architecture"][0] == "Constitution"
    assert board["architecture"][-1] == "Evaluation Results"


def test_gov_001_blocks_high_conviction_on_low_readiness():
    bad = {
        "ticker": "PAYTM",
        "recommendation_readiness": 40,
        "decision": "High Conviction",
        "readiness_band": "high_conviction_allowed",
    }
    out = evaluate_rule("GOV-001", bad)
    assert out["status"] == "FAIL"

    good = {
        "ticker": "PAYTM",
        "recommendation_readiness": 40,
        "decision": "Deferred",
        "readiness_band": "deferred",
        "investment_thesis_status": "INCONCLUSIVE",
    }
    assert evaluate_rule("GOV-001", good)["status"] == "PASS"


def test_gov_006_and_007_inconclusive_separation():
    row = {
        "ticker": "IDEA",
        "gate": "FAIL",
        "evidence_class": "Insufficient",
        "recommendation_readiness": 30,
        "investment_thesis_status": "INCONCLUSIVE",
        "decision": "Deferred",
        "company_quality": 8.0,
        "overall_score": None,
        "not_a_negative_view": True,
    }
    assert evaluate_rule("GOV-006", row)["status"] == "PASS"
    assert evaluate_rule("GOV-007", row)["status"] == "PASS"

    overridden = {**row, "decision": "High Conviction", "readiness_band": "high_conviction_allowed"}
    assert evaluate_rule("GOV-007", overridden)["status"] == "FAIL"


def test_gov_002_missing_price():
    row = {
        "ticker": "X",
        "price_available": False,
        "live_price": False,
        "valuation": 7.5,
        "decision": "Constructive",
        "investment_thesis_status": "FORMED",
        "gate": "PASS",
    }
    assert evaluate_rule("GOV-002", row)["status"] == "FAIL"

    ok = {
        "ticker": "X",
        "price_available": False,
        "live_price": False,
        "valuation": None,
        "decision": "Deferred",
        "investment_thesis_status": "INCONCLUSIVE",
        "gate": "FAIL",
        "failure": {"reason": "LIVE_PRICE_UNAVAILABLE", "stage": "Groww Live Price"},
    }
    assert evaluate_rule("GOV-002", ok)["status"] == "PASS"


def test_assert_ticker_board_shape():
    row = {
        "ticker": "HDFCBANK",
        "recommendation_readiness": 94,
        "decision": "Constructive",
        "gate": "PASS",
        "price_available": True,
        "live_price": True,
        "company_quality": 8.2,
        "versions": {"decision_engine_version": "ide-v1.0.0"},
        "knowledge_snapshot": "2026-07-29T10:00:00Z",
        "market_snapshot": "2026-07-29T15:29:58Z",
    }
    out = assert_ticker(row)
    assert out["passed"] is True
    statuses = {a["rule_id"]: a["status"] for a in out["assertions"]}
    assert statuses["GOV-001"] in {"PASS", "SKIP"}
    assert "GOV-008" in statuses


def _fake_price(ticker: str, force: bool = False) -> dict:
    return {
        "refreshed": True,
        "snapshot": {
            "ltp": 1000.0,
            "stale": False,
            "source_provider": "groww",
            "as_of": "2026-07-29T15:29:58Z",
        },
    }


def _fake_ide(ticker, *, query="", cid=None, company_analysis=None, live_evidence=None):
    readiness = 94.0 if ticker in {"HDFCBANK", "TCS", "INFY", "RELIANCE"} else 45.0
    gate = "PASSED" if readiness >= 80 else "FAILED"
    thesis = "FORMED" if readiness >= 80 else "INCONCLUSIVE"
    decision = "Constructive" if readiness >= 80 else "Deferred"
    return {
        "enabled": True,
        "active": True,
        "ticker": ticker,
        "layers": [
            {"id": "company_quality", "score": 82},
            {"id": "financial_quality", "score": 88 if readiness >= 80 else 25},
            {"id": "valuation", "score": 65},
            {"id": "macro", "score": 80},
            {"id": "technical", "score": 70},
            {"id": "risk", "score": 75},
        ],
        "institutional_readiness_gate": {
            "status": gate,
            "band": "high_conviction_allowed" if readiness >= 90 else "deferred",
            "evidence_confidence_pct": readiness,
            "overall_coverage_pct": readiness,
            "investment_thesis_status": thesis,
            "not_a_negative_view": thesis == "INCONCLUSIVE",
            "company_quality_10": 8.2,
            "missing": [] if readiness >= 80 else ["Financial statements", "Shareholding"],
            "diagnostic_cards": (
                []
                if readiness >= 80
                else [
                    {"key": "financials", "present": False, "label": "Financial statements"},
                    {"key": "ownership", "present": False, "label": "Current shareholding"},
                ]
            ),
        },
        "summary": {
            "action": decision.lower(),
            "evidence_confidence_pct": readiness,
            "readiness_band": "high_conviction_allowed" if readiness >= 90 else "deferred",
            "investment_thesis_status": thesis,
            "company_quality_10": 8.2,
            "gate_blocked": gate == "FAILED",
            "not_a_negative_view": thesis == "INCONCLUSIVE",
        },
        "decision": {"action": decision.lower(), "investment_thesis_status": thesis},
    }


def test_phase6_against_evaluation_lab_results(monkeypatch, tmp_path):
    monkeypatch.setenv("IEL_GOLDEN_STORE_ROOT", str(tmp_path / "golden"))
    monkeypatch.setenv("IEL_GOLDEN_RESULTS_ROOT", str(tmp_path / "results"))

    run_golden_evaluation(
        limit=5,
        persist=True,
        persist_baseline=False,
        compare_previous=False,
        release_id="PR307",
        ide_runner=_fake_ide,
        price_runner=_fake_price,
    )

    report = run_phase6(release_id="PR307", spec_version="v1.0")
    assert report["spec_version"] == "v1.0"
    assert report["n_tickers"] == 5
    board = {g["rule_id"]: g["status"] for g in report["governance_assertions"]}
    assert set(board) == set(FROZEN_RULE_IDS)
    # Every rule reports PASS/FAIL/SKIP — never silent
    assert all(v in {"PASS", "FAIL", "SKIP"} for v in board.values())
    text = format_board(report)
    assert "Governance Assertions" in text
    assert "GOV-001" in text
    assert "GOV-008" in text

    # Persist via production helper
    from institutional_evaluation_lab.production import phase6_governance

    saved = phase6_governance(release_id="PR307", persist=True)
    assert Path(saved["report_path"]).exists()
    disk = json.loads(Path(saved["report_path"]).read_text())
    assert disk["board"][0]["rule_id"] == "GOV-001"
