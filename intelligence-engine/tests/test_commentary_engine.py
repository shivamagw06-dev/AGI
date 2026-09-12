"""PIL — commentary engine."""

from __future__ import annotations

from peer_intelligence.commentary.engine import commentary_for


def test_hdfc_commentary_is_relative_not_standalone():
    out = commentary_for("HDFCBANK")
    assert out["found"] is True
    text = (out["narrative"] or "").lower()
    assert "rank" in text or "percentile" in text
    assert out["trajectory_insight"]
    assert "narrow" in out["trajectory_insight"].lower() or "icici" in out["trajectory_insight"].lower()
    assert "standalone" in (out.get("institutional_rule") or "").lower() or "peer" in (
        out.get("institutional_rule") or ""
    ).lower()


def test_nestle_commentary_mentions_peer_rank():
    out = commentary_for("NESTLEIND")
    assert "rank" in (out["narrative"] or "").lower()
