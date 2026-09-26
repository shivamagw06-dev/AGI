"""PIL — ranking engine."""

from __future__ import annotations

from peer_intelligence.rankings.engine import rankings_for


def test_tcs_financial_quality_ranks():
    out = rankings_for("TCS")
    assert out["found"] is True
    assert out["metric_ranks"]
    ebit = next(r for r in out["metric_ranks"] if r["metric"] == "EBIT_Margin")
    assert ebit["rank"] == 1
    assert "financial_quality" in out["dimensions"] or "margins" in out["dimensions"]
