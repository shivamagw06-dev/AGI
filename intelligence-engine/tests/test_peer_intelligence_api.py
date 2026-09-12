"""PIL — production/API facade + soft-wires."""

from __future__ import annotations

from peer_intelligence.production import (
    admin_page,
    company,
    compare,
    dashboard,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_irs,
)
from peer_intelligence.schema import PIL_VERSION


def test_dashboard_and_quality_gates():
    dash = dashboard()
    assert dash["programme"] == "AGIB_PEER_INTELLIGENCE_LAYER"
    assert dash["pil_version"] == PIL_VERSION
    assert dash["flags"]["PEER_INTELLIGENCE"] is True
    gates = quality_gates()
    assert gates["passed"] is True, gates


def test_company_and_compare():
    out = company("HDFCBANK")
    assert out["enabled"] is True
    assert out["scorecard"]["found"] is True
    cmp = compare(["HDFCBANK", "ICICIBANK"], metric="CASA")
    assert len(cmp["compare"]) == 2


def test_soft_slices_and_admin():
    ba = soft_slice_for_analyst("HDFCBANK", analyst="business")
    assert ba["peer_intelligence"]["enabled"] is True
    assert ba["peer_intelligence"]["narrative"]
    irs = soft_slice_for_irs()
    assert irs["peer_intelligence"]["quality_gates_passed"] is True
    html = admin_page()
    assert "Peer Intelligence Layer" in html
    assert "HDFC" in html or "HDFCBANK" in html


def test_irs_dashboard_includes_pil():
    from academy.regression.production import dashboard as irs_dashboard
    from academy.regression.production import reset_for_tests

    reset_for_tests()
    dash = irs_dashboard()
    assert dash["peer_intelligence"]["enabled"] is True
