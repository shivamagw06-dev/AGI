"""PIL — historical context engine."""

from __future__ import annotations

from peer_intelligence.historical.series import history_for


def test_hdfc_casa_below_own_average():
    out = history_for("HDFCBANK", "CASA")
    assert out["found"] is True
    row = out["series"][0]
    assert row["stats"]["latest"] == 32.3
    assert row["vs_own_5y_avg"] is not None
    assert row["vs_own_5y_avg"] < 0
    assert "below" in row["context"].lower()
