"""PIL — percentile engine."""

from __future__ import annotations

from peer_intelligence.percentile.engine import percentiles_for


def test_hdfc_casa_percentile_and_rank():
    out = percentiles_for("HDFCBANK")
    assert out["found"] is True
    casa = next(p for p in out["percentiles"] if p["metric"] == "CASA")
    assert casa["rank"] >= 1
    assert casa["n"] >= 4
    assert 0 <= casa["percentile"] <= 100
    # Kotak leads CASA in seed panel → HDFC should not be rank 1 on CASA
    assert casa["rank"] >= 2


def test_gnpa_lower_better():
    out = percentiles_for("HDFCBANK")
    gnpa = next(p for p in out["percentiles"] if p["metric"] == "GNPA")
    assert gnpa["lower_better"] is True
    assert gnpa["rank"] == 1  # best (lowest) in seed panel
