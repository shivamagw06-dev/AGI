"""FSE → intelligence soft-wire (Mission Control aggregate board)."""

from __future__ import annotations

from mission_control.aggregate import _soft_institutional_intelligence
from mission_control.agent_map import build_agent_map


def test_soft_institutional_includes_fdo_board():
    out = _soft_institutional_intelligence()
    assert "financial_data_operations" in out
    assert "financial_statements_engine" in out
    fdo = out.get("financial_data_operations")
    if fdo is not None:
        assert fdo.get("workstream_id") == "FSE-FDO" or fdo.get("status")
        assert fdo.get("issues_recommendations") is False
        assert fdo.get("bypasses_fse") is False


def test_agent_map_lists_fse_and_fdo():
    amap = build_agent_map()
    ids = {a["id"] for a in amap.get("agents") or []}
    assert "financial_statements_engine" in ids
    assert "financial_data_operations" in ids
