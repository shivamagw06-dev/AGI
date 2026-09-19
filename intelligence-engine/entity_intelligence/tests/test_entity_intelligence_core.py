"""Unit tests for Entity Intelligence P0 contract."""

from __future__ import annotations

from entity_intelligence.production import analyse, health
from entity_intelligence.schema import (
    STATE_CLARIFICATION_REQUIRED,
    STATE_UNSUPPORTED_ENTITY,
    STATE_VERIFIED_ENTITY,
)


def test_health():
    h = health()
    assert h["ok"] is True
    assert h["version"]


def test_air_india_never_bharti():
    out = analyse("Air India")
    assert out["state"] == STATE_VERIFIED_ENTITY
    assert out.get("ticker") is None
    assert out.get("allow_planner") is False
    assert "air india" in (out.get("canonical_name") or "").lower()
    summary = (out.get("summary") or "").lower()
    assert "bhartiartl" not in summary or "will not substitute" in summary
    assert out.get("ticker") != "BHARTIARTL"


def test_air_india_investment_blocked():
    out = analyse("What is the investment thesis for Air India?")
    assert out["state"] == STATE_VERIFIED_ENTITY
    assert out.get("allow_planner") is False
    assert out.get("ticker") is None


def test_hdfc_clarifies():
    out = analyse("HDFC")
    assert out["state"] == STATE_CLARIFICATION_REQUIRED
    assert out.get("allow_planner") is False


def test_ril_reliance():
    out = analyse("RIL")
    assert out["state"] == STATE_VERIFIED_ENTITY
    assert out.get("ticker") == "RELIANCE"
    assert out.get("allow_planner") is True


def test_unknown_no_substitution():
    out = analyse("XYZ Quantum Robotics")
    assert out["state"] == STATE_UNSUPPORTED_ENTITY
    assert out.get("ticker") is None
    assert out.get("allow_planner") is False


def test_query_planner_air_india_no_ticker():
    from knowledge_unification.query_planner import plan_query

    q = plan_query("Air India")
    assert q.ticker_hint is None
