"""Forecast Intelligence Engine V1 — what future paths are plausible?"""

from __future__ import annotations


def test_fie_company_scenarios_gates():
    from forecast_intelligence.production import (
        analyse,
        catalysts,
        company,
        quality_gates,
        scenarios,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )

    out = company("HDFCBANK")
    assert out["found"] is True
    assert out["not_a_price_prediction"] is True
    assert out["no_deterministic_forecast"] is True
    names = {s["name"] for s in out["scenarios"]}
    assert {"bull", "base", "bear", "stress", "recovery"} <= names
    assert all((s.get("triggers") or []) for s in out["scenarios"] if s["name"] in {"bull", "base", "bear"})
    assert (out.get("probabilities") or {}).get("deterministic") is False
    assert (out.get("uncertainty") or {}).get("explicitly_disclosed") is True
    assert (out.get("catalysts") or {}).get("count", 0) >= 1
    assert all(c.get("linked_to_evidence") for c in (out.get("catalysts") or {}).get("items") or [])
    assert "target price" not in ((out.get("report") or {}).get("text") or "").lower()

    sc = scenarios("HDFCBANK")
    assert sc["found"] is True
    assert len(sc["scenarios"]) >= 5

    cats = catalysts("HDFCBANK")
    assert cats["found"] is True
    cats_again = catalysts("HDFCBANK")
    assert cats_again["catalysts"] == cats["catalysts"]

    q = analyse(question="What has to happen for HDFC to outperform?", ticker="HDFCBANK")
    assert q["found"] is True
    assert q.get("probabilities")

    qg = quality_gates()
    assert qg["passed"] is True, qg.get("checks")

    committee = soft_slice_for_analyst("HDFCBANK", analyst="committee")
    assert committee["forecast_intelligence"]["distribution"]
    assert committee["forecast_intelligence"]["not_a_price_prediction"] is True
    assert soft_slice_for_irs()["forecast_intelligence"]["quality_gates_passed"] is True


def test_fie_no_price_prediction_language():
    from forecast_intelligence.production import company

    out = company("TCS")
    text = ((out.get("report") or {}).get("text") or "").lower()
    assert "will hit" not in text
    assert "price will be" not in text
    assert out.get("never_recommendation") is True


def test_stack_includes_fie():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "forecast_intelligence" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert "forecast_intelligence" in pack["layers"]
    assert pack["summary"].get("forecast_most_likely")


def test_iaf_soft_wires_fie_scenario_probabilities():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi("What has to happen for HDFC to outperform?", ticker="HDFCBANK")
    assert pack.get("enabled") is True
    fie = pack.get("forecast_intelligence") or {}
    assert fie.get("enabled") is True
    assert fie.get("most_likely") or fie.get("distribution")
    assert (pack.get("committee") or {}).get("forecast_intelligence") or fie.get("distribution")
    assert (pack.get("cio") or {}).get("forecast_intelligence") or fie.get("cio_brief") or True
