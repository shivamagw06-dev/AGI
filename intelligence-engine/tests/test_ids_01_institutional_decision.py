"""IDS-01 — Institutional Decision System tests (no LLM)."""

from __future__ import annotations

from institutional_decision.decision_engine import generate_decision
from institutional_decision.decision_validator import validate_decision
from institutional_decision.diagnostics import build_diagnostics
from institutional_decision import history as decision_history
from institutional_decision.models import InstitutionalDecision
from institutional_decision.production import decide_company, get_company_decision, health
from institutional_decision.schema import IDS_WORKSTREAM_ID
from institutional_reporting.composer import compose_report
from institutional_reporting.fixtures import get_fixture
from institutional_reporting.reason_composer import compose_reasons


def setup_function(_fn=None):
    decision_history.reset_for_tests()


def test_health():
    h = health()
    assert h["workstream_id"] == IDS_WORKSTREAM_ID
    assert h["owns_recommendation"] is True
    assert h["llm"] is False


def test_decision_generation_buy_rule():
    d = generate_decision(
        reasons=["bq_strong", "fq_strong", "val_cheap"],
        valuation="Cheap",
        risks=["minor"],
        confidence=80,
        business_quality=92,
        financial_quality="Strong",
        overall_risk="Low",
        ticker="TESTBUY",
        unknowns=["credit_demand"],
        evidence_ids=["FIRE-06", "AR-FY25"],
    )
    assert d.recommendation == "BUY"
    assert d.conviction in {"MEDIUM", "HIGH"}
    assert d.decision_id
    assert d.decision_version == 1
    assert d.evidence_snapshot_id
    assert d.upgrade_conditions
    assert d.downgrade_conditions
    assert d.monitoring_items
    assert d.decision_graph is not None
    assert validate_decision(
        d, business_quality=92, valuation="Cheap", overall_risk="Low"
    ).ok


def test_decision_generation_hold_rule():
    d = generate_decision(
        valuation="Fair",
        confidence=67,
        business_quality=91,
        financial_quality="Stable",
        overall_risk="Moderate",
        ticker="AXISBANK",
        unknowns=["Duration of liability cost pressure"],
        evidence_ids=["FIRE-06"],
        risks=["Credit costs"],
    )
    assert d.recommendation == "HOLD"
    assert d.conviction == "LOW"


def test_decision_generation_sell_rule():
    d = generate_decision(
        valuation="Expensive",
        confidence=55,
        business_quality=40,
        financial_quality="Weak",
        overall_risk="High",
        ticker="TESTSELL",
        unknowns=["recovery_path"],
        evidence_ids=["FIRE-06"],
        risks=["NPAs rising"],
    )
    assert d.recommendation == "SELL"
    assert d.conviction in {"MEDIUM", "HIGH"}


def test_validator_rejects_buy_low():
    d = generate_decision(
        valuation="Cheap",
        confidence=70,
        business_quality=90,
        financial_quality="Strong",
        overall_risk="Low",
        ticker="X",
        unknowns=["u"],
        evidence_ids=["E1"],
    )
    bad = InstitutionalDecision.from_dict(
        {**d.to_dict(), "recommendation": "BUY", "conviction": "LOW"}
    )
    v = validate_decision(bad)
    assert v.ok is False
    assert any("BUY with LOW" in e for e in v.errors)


def test_validator_rejects_sell_excellent_cheap_low():
    d = generate_decision(
        valuation="Cheap",
        confidence=70,
        business_quality=40,
        financial_quality="Weak",
        overall_risk="High",
        ticker="Y",
        unknowns=["u"],
        evidence_ids=["E1"],
    )
    bad = InstitutionalDecision.from_dict({**d.to_dict(), "recommendation": "SELL", "conviction": "MEDIUM"})
    v = validate_decision(bad, business_quality=95, valuation="Cheap", overall_risk="Low")
    assert v.ok is False
    assert any("SELL with Excellent" in e for e in v.errors)


def test_validator_rejects_missing_monitoring_unknowns_evidence():
    d = generate_decision(
        valuation="Fair",
        confidence=60,
        business_quality=80,
        financial_quality="Strong",
        overall_risk="Moderate",
        ticker="Z",
        unknowns=["u"],
        evidence_ids=["E1"],
    )
    bad = InstitutionalDecision.from_dict(
        {
            **d.to_dict(),
            "unknowns": [],
            "monitoring_items": [],
            "evidence_ids": [],
        }
    )
    v = validate_decision(bad)
    assert v.ok is False
    assert any("unknowns" in e for e in v.errors)
    assert any("monitoring" in e for e in v.errors)
    assert any("evidence" in e for e in v.errors)


def test_upgrade_downgrade_conditions_and_diagnostics():
    d = generate_decision(
        valuation="Fair",
        confidence=70,
        business_quality=90,
        financial_quality="Strong",
        overall_risk="Moderate",
        ticker="ICICIBANK",
        unknowns=["cycle"],
        evidence_ids=["FIRE-06", "QR-Q4"],
    )
    v = validate_decision(d, business_quality=90, valuation="Fair", overall_risk="Moderate")
    diag = build_diagnostics(d, v)
    assert diag["validator_result"] == "PASS"
    assert diag["upgrade_conditions"]
    assert diag["downgrade_conditions"]
    assert diag["decision_id"] == d.decision_id


def test_history_versions_transitions():
    d1 = generate_decision(
        valuation="Fair",
        confidence=67,
        business_quality=91,
        financial_quality="Stable",
        overall_risk="Moderate",
        ticker="AXISBANK",
        unknowns=["u"],
        evidence_ids=["E1"],
        previous_version=0,
    )
    decision_history.record(d1)
    d2 = generate_decision(
        valuation="Cheap",
        confidence=80,
        business_quality=92,
        financial_quality="Strong",
        overall_risk="Low",
        ticker="AXISBANK",
        unknowns=["u"],
        evidence_ids=["E1", "E2"],
        previous_version=d1.decision_version,
    )
    entry = decision_history.record(d2)
    assert d2.decision_version == 2
    assert "HOLD->BUY" in entry.transition or entry.previous_recommendation == "HOLD"
    hist = decision_history.history_for("AXISBANK")
    assert len(hist) == 2
    assert hist[0]["decision"]["decision_version"] == 1
    assert hist[1]["decision"]["decision_version"] == 2


def test_api_decide_and_get_with_history():
    out = decide_company({"ticker": "AXISBANK", "include_history": True})
    assert out["ok"] is True
    assert out["decision"]["recommendation"] == "HOLD"
    assert out["diagnostics"]["quality_gate_pass"] is True
    assert out.get("history")
    got = get_company_decision("AXISBANK", include_history=True)
    assert got["ok"] is True
    assert got["decision"]["decision_id"] == out["decision"]["decision_id"]


def test_report_consumes_decision_not_fixture_recommendation():
    """Fixture ICICIBANK says BUY; IDS rules → HOLD. Report must render decision."""
    report = compose_report(get_fixture("ICICIBANK"))
    assert report.ok is True
    assert report.decision is not None
    assert report.recommendation == report.decision.recommendation
    assert report.recommendation == "HOLD"
    assert report.decision.decision_id
    assert report.diagnostics.get("decision_system") is True


def test_integration_banks_same_structure_different_decisions():
    payloads = {}
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        out = decide_company({"ticker": ticker})
        assert out["ok"] is True, out.get("validation_errors")
        d = out["decision"]
        assert d["decision_id"]
        assert d["upgrade_conditions"]
        assert d["downgrade_conditions"]
        assert d["monitoring_items"]
        assert d["unknowns"]
        assert d["decision_graph"]["nodes"]
        assert d["llm"] is False
        payloads[ticker] = (
            d["recommendation"],
            d["conviction"],
            d["confidence"],
            tuple(d["supporting_reasons"][:3]),
            tuple(d["unknowns"][:1]),
            d["score"],
        )
        report = compose_report(get_fixture(ticker))
        assert report.recommendation == d["recommendation"]
    assert len(set(payloads.values())) >= 2


def test_cli_module():
    from institutional_decision.__main__ import main

    assert main(["--health"]) == 0
