"""IRE-01 — Institutional Reporting Engine tests (no LLM)."""

from __future__ import annotations

import json

from institutional_reporting.composer import compose_report
from institutional_reporting.confidence import explain_confidence
from institutional_reporting.fixtures import FIXTURES, get_fixture
from institutional_reporting.models import EvidenceItem, InstitutionalReportInput
from institutional_reporting.production import compose_company_report, health
from institutional_reporting.schema import REPORT_SECTIONS, SECTION_TITLES
from institutional_reporting.validator import validate_input


def _base_input(**overrides):
    data = {
        "ticker": "AXISBANK",
        "company_name": "Axis Bank",
        "sector": "Banking",
        "recommendation": "HOLD",
        "conviction": "LOW",
        "confidence": 67,
        "horizon": "Medium",
        "business_quality": 91,
        "financial_quality": "Stable",
        "valuation": "Fair",
        "overall_risk": "Moderate",
        "thesis": ["Franchise improving"],
        "risks": ["Credit costs"],
        "catalysts": ["CASA"],
        "watch_items": ["NIM"],
        "evidence": [
            {
                "evidence_id": "FIRE-06",
                "label": "Business Quality Pack",
                "source_type": "Annual Report",
                "section_keys": list(REPORT_SECTIONS),
            }
        ],
    }
    data.update(overrides)
    return InstitutionalReportInput.from_dict(data)


def test_health_no_llm():
    h = health()
    assert h["workstream_id"] in {"IRE-01", "IRE-02"}
    assert h["llm"] is False
    assert h["gemini"] is False
    assert h["openai"] is False
    assert h["sections"] == list(REPORT_SECTIONS)


def test_recommendation_hold_low_pass():
    v = validate_input(_base_input(recommendation="HOLD", conviction="LOW"))
    assert v.ok is True


def test_recommendation_buy_low_fail():
    v = validate_input(_base_input(recommendation="BUY", conviction="LOW"))
    assert v.ok is False
    assert any("impossible combination" in e for e in v.errors)


def test_recommendation_sell_excellent_cheap_low_risk_fail():
    v = validate_input(
        _base_input(
            recommendation="SELL",
            conviction="MEDIUM",
            business_quality=95,
            valuation="Cheap",
            overall_risk="Low",
        )
    )
    assert v.ok is False
    assert any("SELL with Excellent" in e for e in v.errors)


def test_confidence_always_explained():
    conf = explain_confidence(_base_input())
    assert conf["score"] == 67
    assert conf["positive_drivers"]
    assert conf["negative_drivers"]
    assert conf["unknowns"]
    assert "Positive Drivers" in conf["body"]
    assert "Negative Drivers" in conf["body"]
    assert "Unknowns" in conf["body"]
    assert "67%" in conf["body"]


def test_evidence_rendering_in_paragraphs():
    report = compose_report(_base_input())
    assert report.ok is True
    bq = next(s for s in report.sections if s.key == "business_quality")
    # IRE-02 section contract embeds Evidence (not legacy "Supported by" block).
    assert "Evidence" in bq.body
    assert "FIRE-06" in bq.body
    assert bq.evidence_ids
    assert "Conclusion" in bq.body
    assert "Unknowns" in bq.body


def test_missing_section_impossible_fixed_structure():
    report = compose_report(get_fixture("AXISBANK"))
    assert [s.key for s in report.sections] == list(REPORT_SECTIONS)
    assert [s.title for s in report.sections] == [SECTION_TITLES[k] for k in REPORT_SECTIONS]


def test_report_generation_deterministic():
    inp = get_fixture("AXISBANK")
    a = compose_report(inp)
    b = compose_report(inp)
    assert a.ok and b.ok
    assert a.text == b.text
    assert a.input_fingerprint == b.input_fingerprint
    assert a.llm is False


def test_rejected_without_thesis():
    report = compose_report(_base_input(thesis=[]))
    assert report.rejected is True
    assert report.ok is False


def test_quality_gates_require_bottom_line():
    report = compose_report(get_fixture("AXISBANK"))
    assert report.quality_gates["bottom_line_exists"] is True
    assert "Bottom Line" in report.text


def test_integration_banks_identical_structure_different_facts():
    texts = {}
    structures = []
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        report = compose_report(get_fixture(ticker))
        assert report.ok is True, report.validation_errors
        keys = [s.key for s in report.sections]
        structures.append(keys)
        texts[ticker] = report.text
        assert report.recommendation in {"BUY", "HOLD", "SELL", "AVOID", "WATCH"}
        assert "Institutional View" in report.text
        assert "Investment Thesis" in report.text
        assert "Evidence" in report.text
        assert "Bottom Line" in report.text
        assert "gemini" not in report.text.lower()
        assert "openai" not in report.text.lower()
    assert structures[0] == structures[1] == structures[2] == structures[3]
    # Facts differ across namesakes
    assert len(set(texts.values())) == 4
    assert "Axis Bank" in texts["AXISBANK"]
    assert "Kotak" in texts["KOTAKBANK"]
    assert "ICICI" in texts["ICICIBANK"]
    assert "HDFC" in texts["HDFCBANK"]


def test_api_compose_company_report_ticker_fixture():
    out = compose_company_report({"ticker": "AXISBANK"})
    assert out["ok"] is True
    assert out["ticker"] == "AXISBANK"
    assert out["llm"] is False
    assert len(out["sections"]) == len(REPORT_SECTIONS)


def test_api_compose_from_full_input_dict():
    payload = get_fixture("ICICIBANK").to_dict()
    out = compose_company_report(payload)
    assert out["ok"] is True
    # IDS-01 owns recommendation — Fair/Moderate quality stack → HOLD (not fixture BUY).
    assert out["recommendation"] in {"BUY", "HOLD", "SELL", "AVOID", "WATCH"}
    assert out.get("decision_system") is True
    assert out.get("decision", {}).get("decision_id")


def test_cli_module_importable():
    from institutional_reporting.__main__ import main

    assert main(["--health"]) == 0
