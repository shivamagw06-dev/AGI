"""FIL — production/API facade + soft-wires."""

from __future__ import annotations

from filing_intelligence.ingestion.store import reset_for_tests
from filing_intelligence.production import (
    admin_page,
    company,
    dashboard,
    evidence,
    history,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_irs,
    timeline,
)
from filing_intelligence.schema import FIL_VERSION


def setup_function() -> None:
    reset_for_tests()


def test_dashboard_and_quality_gates():
    dash = dashboard()
    assert dash["programme"] == "AGIB_FILING_INTELLIGENCE_LAYER"
    assert dash["fil_version"] == FIL_VERSION
    assert dash["flags"]["FILING_INTELLIGENCE"] is True
    gates = quality_gates()
    assert gates["passed"] is True, gates


def test_company_history_timeline_evidence():
    out = company("HDFCBANK")
    assert out["found"] is True
    assert "CET1" in out["narrative"] or "filing" in out["narrative"].lower()
    assert history("HDFCBANK")["history"]["count"] >= 3
    assert len(timeline("HDFCBANK")["timeline"]) >= 2
    ev = evidence("HDFCBANK")
    assert ev["evidence"]["count"] >= 5
    assert ev["evidence"]["tier1_count"] >= 1 or any(
        f.get("evidence_tier") in {1, 2, 4} for f in ev["evidence"]["facts"]
    )


def test_soft_slices_admin_irs():
    fa = soft_slice_for_analyst("HDFCBANK", analyst="financial")
    assert fa["filing_intelligence"]["enabled"] is True
    assert fa["filing_intelligence"].get("history")
    irs = soft_slice_for_irs()
    assert irs["filing_intelligence"]["quality_gates_passed"] is True
    html = admin_page()
    assert "Filing Intelligence Layer" in html

    from academy.regression.production import dashboard as irs_dashboard
    from academy.regression.production import reset_for_tests as irs_reset

    irs_reset()
    dash = irs_dashboard()
    assert dash["filing_intelligence"]["enabled"] is True
