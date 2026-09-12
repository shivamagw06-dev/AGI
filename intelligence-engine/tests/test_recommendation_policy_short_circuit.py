"""Recommendation bait must refuse before RQ / retrieval / IRP fan-out."""

from __future__ import annotations

import time

from app.ui.service import UiService, _is_recommendation_bait


def test_recommendation_bait_detector():
    assert _is_recommendation_bait("Should I buy HDFC Bank tomorrow?")
    assert _is_recommendation_bait("Should I sell Reliance?")
    assert not _is_recommendation_bait(
        "Compare HDFC Bank vs ICICI Bank on valuation and risks; "
        "do not give a buy or sell recommendation."
    )
    assert not _is_recommendation_bait(
        "Explain HDFC Bank's earnings; no recommendation is required."
    )
    assert _is_recommendation_bait(
        "Do not give a recommendation, but should I buy HDFC Bank?"
    )
    assert not _is_recommendation_bait("What did Meta say in Q2 2026 about AI capex?")
    assert not _is_recommendation_bait("What are the key risks for HDFC Bank?")


def test_smoke06_short_circuits_under_two_seconds():
    ui = UiService()
    t0 = time.perf_counter()
    view = ui.search("Should I buy HDFC Bank tomorrow?")
    elapsed = time.perf_counter() - t0
    data = view.model_dump()
    orch = data.get("ask_orchestration") or {}
    deg = data.get("degradation") or {}

    assert elapsed < 2.0, f"recommendation path too slow: {elapsed:.2f}s"
    assert deg.get("short_circuit") == "recommendation_policy"
    assert orch.get("short_circuit") == "recommendation_policy"
    assert data.get("answer_policy") == "no_buy_sell_recommendation"
    text = " ".join(
        [
            str(data.get("executive_summary") or ""),
            str((data.get("answer") or {}).get("summary") or ""),
        ]
    ).lower()
    assert "does not issue buy or sell" in text or "no transactional recommendation" in text
    # Must not look like a full research hang path
    assert orch.get("rq_stack") == "skipped_recommendation_policy"
    assert orch.get("completed") is True
    assert orch.get("timeout") is False
    entities = data.get("entities") or {}
    ticker = str(entities.get("ticker") or "").upper()
    assert ticker in {"HDFCBANK", "HDFC BANK"} or "HDFC" in text.upper()
