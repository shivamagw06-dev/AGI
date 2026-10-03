"""Unit tests for Phase 3.2 Investment Intelligence (pre-Ask wiring)."""

from __future__ import annotations

from investment_intelligence.policy import assert_no_recommendation, has_recommendation_leak
from investment_intelligence.production import analyse, health, soft_slice_for_ask_agi
from investment_intelligence.profiles import list_profiles, resolve_entity
from investment_intelligence.schema import ASK_WIRED, IIE_VERSION, RECOMMENDATION_POLICY


def test_ask_wired_via_kul():
    assert ASK_WIRED is True
    h = health()
    assert h["ask_wired"] is True
    assert h["recommendation_policy"] == RECOMMENDATION_POLICY
    soft = soft_slice_for_ask_agi("What is the investment thesis for TCS?")
    assert soft.get("ask_wired") is True
    assert soft.get("found") is True


def test_profiles_resolve():
    assert resolve_entity("HDFC Bank") == "hdfc_bank"
    assert resolve_entity("SaaS") == "software_industry"
    assert len(list_profiles()) >= 15


def test_thesis_no_recommendation():
    out = analyse("What is the investment thesis for TCS?", entity="tcs")
    assert out["ok"] is True
    assert out["recommendation"] is None
    assert "no_buy_sell" in out["recommendation_policy"]
    assert assert_no_recommendation(out)
    assert "tcs" in out["summary"].lower() or "quality" in out["summary"].lower()


def test_committee_no_buy_sell():
    out = analyse("Run an investment committee simulation for Reliance Industries.", entity="reliance")
    assert out.get("committee")
    low = out["summary"].lower()
    assert "no buy" in low or "no sell" in low
    assert not has_recommendation_leak(out["summary"])


def test_scenarios_no_price_targets():
    out = analyse("Outline bull, base, and bear scenarios for Infosys.", entity="infosys")
    sc = out.get("scenarios") or {}
    assert "scenarios" in sc
    for case in ("bull", "base", "bear"):
        assert case in sc["scenarios"]
        assert sc["scenarios"][case].get("price_target") is None


def test_quality_compare():
    out = analyse("Compare Asian Paints and Berger from a quality perspective.")
    assert out["ok"] is True
    assert "asian" in out["summary"].lower()
    assert "berger" in out["summary"].lower()


def test_consumes_industry_dna_methods():
    out = analyse("What drives valuation for HDFC Bank?", entity="hdfc_bank")
    val = out.get("valuation") or {}
    methods = " ".join(val.get("valuation_methods") or []).lower()
    assert "p/b" in methods or "book" in (val.get("summary") or "").lower()


def test_version():
    assert IIE_VERSION.startswith("3.2")
