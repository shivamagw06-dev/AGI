"""IRE-02 — Deterministic Reason Composer tests (no LLM)."""

from __future__ import annotations

from institutional_reporting.composer import compose_report
from institutional_reporting.explanation import (
    explain_business_quality,
    explain_financial_quality,
    explain_recommendation,
    explain_risk,
    explain_valuation,
)
from institutional_reporting.fixtures import get_fixture
from institutional_reporting.production import compose_company_report, health, report_for_ticker
from institutional_reporting.reason_composer import compose_reasons
from institutional_reporting.reasoning import Reason
from institutional_reporting.schema import REPORT_SECTIONS, IRE_VERSION, VALIDATOR_VERSION
from institutional_reporting.validator import validate_reason, validate_reasons


def test_health_reason_composer():
    h = health()
    assert h["workstream_id"] == "IRE-02"
    assert h["reason_composer"] is True
    assert h["llm"] is False
    assert h["version"] == IRE_VERSION


def test_reason_creation_and_validation():
    reason = Reason(
        title="Business Quality",
        conclusion="Strong",
        confidence=0.84,
        supporting_evidence=("FIRE-06", "Annual Report"),
        supporting_points=("ROE above peer median", "Asset quality stable"),
        contradicting_points=("NIM under pressure",),
        unknowns=("Future credit demand",),
        section_key="business_quality",
    )
    assert validate_reason(reason) == []


def test_empty_reason_fails():
    reason = Reason(title="", conclusion="", confidence=-1.0)
    errors = validate_reason(reason, section_key="business_quality")
    assert errors


def test_explanation_engine_returns_structured_reasons():
    inp = get_fixture("AXISBANK")
    for fn in (
        explain_business_quality,
        explain_financial_quality,
        explain_valuation,
        explain_risk,
        explain_recommendation,
    ):
        reason = fn(inp)
        assert isinstance(reason, Reason)
        assert reason.conclusion
        assert reason.supporting_evidence
        assert reason.supporting_points
        assert reason.contradicting_points
        assert reason.unknowns
        assert 0.0 <= reason.confidence <= 1.0
        # No prose templates in explanation layer — facts/tokens only
        assert "remains strong because" not in " ".join(reason.supporting_points).lower()


def test_reason_graph_covers_all_sections():
    graph = compose_reasons(get_fixture("KOTAKBANK"))
    assert validate_reasons(graph).ok is True
    assert [r.section_key for r in graph.reasons] == list(REPORT_SECTIONS)


def test_report_generated_from_reasoning():
    report = compose_report(get_fixture("AXISBANK"))
    assert report.ok is True
    assert report.reasons
    assert len(report.reasons) == len(REPORT_SECTIONS)
    for section in report.sections:
        assert section.reason is not None
        assert "Conclusion" in section.body
        assert "Supporting Reasons" in section.body
        assert "Contradicting Reasons" in section.body
        assert "Unknowns" in section.body
        assert "Evidence" in section.body
        assert "Confidence" in section.body
        assert "Explanation" in section.body


def test_diagnostics_included():
    report = compose_report(get_fixture("ICICIBANK"))
    d = report.diagnostics
    assert d["ire_version"] == IRE_VERSION
    assert d["validator_version"] == VALIDATOR_VERSION
    assert d["reason_object_count"] == len(REPORT_SECTIONS)
    assert d["evidence_count"] > 0
    assert d["quality_gate"] == "PASS"
    assert d["llm"] is False


def test_evidence_traceable_and_unknowns_mandatory():
    report = compose_report(get_fixture("HDFCBANK"))
    for reason in report.reasons:
        assert reason.supporting_evidence
        assert reason.unknowns
        assert reason.contradicting_points


def test_api_include_reasons_flag():
    full = report_for_ticker("AXISBANK", include_reasons=True)
    assert full["ok"] is True
    assert full.get("reasons")
    assert full.get("diagnostics")
    slim = report_for_ticker("AXISBANK", include_reasons=False)
    assert slim["ok"] is True
    assert "reasons" not in slim
    assert slim.get("diagnostics")


def test_integration_banks_different_reasoning_same_structure():
    graphs = {}
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        report = compose_report(get_fixture(ticker))
        assert report.ok is True, report.validation_errors
        keys = [r.section_key for r in report.reasons]
        assert keys == list(REPORT_SECTIONS)
        # Fingerprint of supporting points across sections
        graphs[ticker] = tuple(
            (r.section_key, r.conclusion, tuple(r.supporting_points[:2]), tuple(r.unknowns[:1]))
            for r in report.reasons
        )
        assert "gemini" not in report.text.lower()
    assert len({graphs[t] for t in graphs}) == 4


def test_deterministic_reason_pipeline():
    inp = get_fixture("AXISBANK")
    a = compose_report(inp)
    b = compose_report(inp)
    assert a.text == b.text
    assert [r.to_dict() for r in a.reasons] == [r.to_dict() for r in b.reasons]
    assert a.input_fingerprint == b.input_fingerprint


def test_compose_company_report_post():
    out = compose_company_report({"ticker": "AXISBANK", "include_reasons": True})
    assert out["ok"] is True
    assert out["reason_composer"] is True
    assert out["diagnostics"]["quality_gate_pass"] is True
