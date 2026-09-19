"""Evidence Intelligence Layer V1 — source attribution, peers/history, confidence."""

from __future__ import annotations

from academy.evidence.attach import enrich_case, support_statement
from academy.evidence.confidence import decompose_confidence
from academy.evidence.production import (
    case_pack,
    dashboard,
    explain_confidence,
    quality_gates,
    soft_slice_for_irs,
)
from academy.evidence.schema import EIL_VERSION


def test_confidence_decomposition_explainable():
    out = decompose_confidence(evidence=80, historical=40, peer=40, macro=70)
    assert out["confidence"] == round(80 * 0.45 + 40 * 0.20 + 40 * 0.20 + 70 * 0.15, 2)
    assert set(out["breakdown"]) == {"evidence", "historical", "peer", "macro"}
    assert "Evidence" in out["explain"]
    assert out["weights"]["evidence"] == 0.45


def test_live_case_11_sources_and_no_prior_as_fact():
    case = enrich_case("acs_live_11_jul2026")
    assert case["case_id"] == "acs_live_11_jul2026"
    claims = case["claims"]
    facts = [c for c in claims if c["epistemic_label"] == "fact"]
    priors = [c for c in claims if c["epistemic_label"] == "prior"]
    street = [c for c in claims if c["epistemic_label"] == "street"]

    assert len(facts) >= 3
    assert all(c["attached_sources"] for c in facts)
    assert all(c["is_evidence"] is False for c in priors)
    assert street
    for c in street:
        pubs = " ".join(c["traceability"]["publishers"]).lower()
        assert "bloomberg" in pubs or "morgan stanley" in pubs
        assert "street" not in (c["statement"] or "").lower() or "bloomberg" in c["statement"].lower()

    assert (case["summary"] or {}).get("open_gaps", 0) >= 1
    assert len(case["decision_triggers"]) >= 3
    assert len(case["transmission_macro"]) >= 7


def test_support_statement_finds_nim_claim():
    hit = support_statement("HDFC Bank NIM declined versus prior quarter")
    assert hit["supports"]
    top = hit["supports"][0]
    assert top["epistemic_label"] in {"fact", "street", "judgement"}
    assert "breakdown" in (top.get("confidence_breakdown") or {})


def test_quality_gates_and_dashboard():
    gates = quality_gates()
    assert gates["passed"] is True, gates
    dash = dashboard()
    assert dash["programme"] == "AGIB_EVIDENCE_INTELLIGENCE_LAYER"
    assert dash["eil_version"] == EIL_VERSION
    pack = case_pack("acs_live_11_jul2026")
    assert pack["enabled"] is True
    assert pack["case_id"] == "acs_live_11_jul2026"


def test_explain_confidence_api_shape():
    out = explain_confidence(evidence=90, historical=50, peer=30, macro=60)
    assert out["confidence"] > 0
    assert out["contributions"]["evidence"] > out["contributions"]["peer"]


def test_soft_slice_for_irs():
    slice_ = soft_slice_for_irs()
    eil = slice_["evidence_intelligence"]
    assert eil["enabled"] is True
    assert eil["quality_gates_passed"] is True
    assert eil["version"] == EIL_VERSION


def test_irs_dashboard_includes_eil_soft_slice():
    from academy.regression.production import dashboard as irs_dashboard
    from academy.regression.production import reset_for_tests

    reset_for_tests()
    dash = irs_dashboard()
    assert "evidence_intelligence" in dash
    assert dash["evidence_intelligence"]["enabled"] is True
