"""Management Intelligence Engine V1 — can management be trusted?"""

from __future__ import annotations

from management_intelligence.dna.classify import classify_dna
from management_intelligence.pipeline import analyse_management
from management_intelligence.production import (
    admin_page,
    company,
    dashboard,
    guidance,
    history,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_irs,
)
from management_intelligence.schema import MII_VERSION
from filing_intelligence.ingestion.store import reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_hdfc_trust_assessment_not_commentary_dump():
    out = analyse_management("HDFCBANK")
    assert out["found"] is True
    assert out["primary_question"].startswith("Can this management team be trusted")
    conf = out["confidence"]
    assert 0 < conf["confidence"] <= 100
    assert conf["weights"]["credibility"] == 0.35
    assert out["guidance"]["guidance_score"] is not None
    assert out["credibility"]["n"] >= 1
    assert out["dna"]["primary"]
    assert out["evidence"]["count"] >= 1
    assert out["decision_journal"]
    # must surface open concerns from FDI liability pressure / claim miss
    assert out["open_concerns"]
    report = out["report"]
    assert "trusted" in report["executive_summary"].lower() or "confidence" in report["cio_brief"].lower()
    assert "buy rating" not in (report.get("text") or "").lower()


def test_management_dna_evidence_driven():
    dna = classify_dna(
        priors=["Professional Steward", "Operator"],
        capital={"capital_allocation": 80, "value_creating": 2, "value_destructive": 0, "decisions": [], "acquisitions": []},
        execution={"execution": 75, "completed": 1, "items": [{"status": "completed"}]},
        guidance={"historical_accuracy": 70},
        credibility={"credibility": 70},
        acquisitions=[],
    )
    assert dna["primary"] in {
        "Professional Steward",
        "Operator",
        "Capital Allocator",
        "Value Creator",
        "Growth Builder",
    }
    assert dna["evolving"] is True


def test_nestle_and_tcs_profiles():
    nestle = analyse_management("NESTLEIND")
    assert nestle["found"]
    assert nestle["dna"]["primary"]
    tcs = analyse_management("TCS")
    assert tcs["found"]
    assert (tcs["credibility"] or {}).get("credibility", 0) >= 50


def test_api_facade_quality_gates_admin_irs():
    assert dashboard()["mii_version"] == MII_VERSION
    assert company("HDFCBANK")["found"] is True
    assert guidance("HDFCBANK")["guidance"]["n"] >= 1
    assert history("HDFCBANK")["timeline"]
    gates = quality_gates()
    assert gates["passed"] is True, gates
    ba = soft_slice_for_analyst("HDFCBANK", analyst="business")
    assert ba["management_intelligence"]["desk"]["dna"]
    fa = soft_slice_for_analyst("HDFCBANK", analyst="financial")
    assert fa["management_intelligence"]["desk"]["capital_allocation"]
    assert "Management Intelligence Engine" in admin_page()
    assert soft_slice_for_irs()["management_intelligence"]["quality_gates_passed"] is True

    from academy.regression.production import dashboard as irs_dashboard
    from academy.regression.production import reset_for_tests as irs_reset

    irs_reset()
    dash = irs_dashboard()
    assert dash["management_intelligence"]["enabled"] is True
