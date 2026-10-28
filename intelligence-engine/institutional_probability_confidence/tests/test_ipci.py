"""Sprint 9.4 — Institutional Probability & Confidence Intelligence tests."""

from __future__ import annotations

from institutional_probability_confidence.production import (
    assessment,
    confidence_company,
    dashboard,
    health,
    probability_company,
    probability_sector,
)
from institutional_probability_confidence.schema import NO_IPCI_JUDGMENT
from institutional_scenario_intelligence.production import company as isi_company


def test_ipci_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "IPCI"
    assert h["providers_queried_always"] == []
    assert "guess_without_evidence" in h["does_not"]


def test_infosys_probabilities_sum_to_100() -> None:
    out = probability_company("INFY")
    assert out["providers_queried"] == []
    assert out["probability_sum_pct"] == 100
    dist = out["distribution"]
    assert set(dist) == {"Bull", "Base", "Bear"}
    assert sum(dist.values()) == 100
    # Institutional Base usually most likely
    assert dist["Base"] >= dist["Bull"]
    assert dist["Base"] >= dist["Bear"]
    assert dist["Bull"] >= 5 and dist["Bear"] >= 5
    for p in out["probabilities"]:
        assert p["probability_pct"] > 0
        assert p["note"]


def test_confidence_independent_of_probability() -> None:
    """Bull can be less probable yet still highly confident in the assessment."""
    probs = probability_company("INFY")
    conf = confidence_company("INFY")
    assert conf["providers_queried"] == []
    assert conf["confidence"]["overall_pct"] >= 35
    assert "evidence_quality_pct" in conf["confidence"]
    assert "knowledge_freshness_pct" in conf["confidence"]
    assert conf["confidence"]["components"]["rule"]
    # Independence: most-likely scenario need not have unique confidence identity
    dist = probs["distribution"]
    most = max(dist, key=dist.get)
    per = conf["per_scenario_confidence"]
    assert most in per
    assert all(35 <= v <= 99 for v in per.values())


def test_forecast_assessment_infosys() -> None:
    out = assessment("INFY")
    assert out["providers_queried"] == []
    assert out["is_recommendation"] is False
    assert out["is_price_prediction"] is False
    assert out["probability_sum_pct"] == 100
    assert out["overall_forecast_quality_pct"] >= 40
    assert out["missing_evidence"]
    assert "Updated Management Guidance" in out["missing_evidence"] or out["missing_evidence"]
    by = {a["scenario"]: a for a in out["assessments"]}
    assert set(by) == {"Bull", "Base", "Bear"}
    for name, a in by.items():
        assert a["probability_pct"] == out["distribution"][name]["probability_pct"]
        assert a["confidence_pct"] >= 35
        assert a["supporting_evidence"]
        assert a["missing_evidence"] is not None
    # No trading language in assessments content
    content = str(out["assessments"]).lower()
    assert "buy" not in content
    assert "sell" not in content
    assert "target price" not in content
    for item in NO_IPCI_JUDGMENT:
        assert item in out["does_not"]


def test_assessment_from_explicit_scenario_report() -> None:
    report = isi_company("HDFCBANK")
    out = assessment(scenario_report=report, scope="company", entity="HDFCBANK")
    assert out["entity"] == "HDFCBANK"
    assert out["scenario_report_id"] == report["report_id"]
    assert out["probability_sum_pct"] == 100


def test_sector_probability() -> None:
    out = probability_sector("information_technology")
    assert out["probability_sum_pct"] == 100
    assert sum(out["distribution"].values()) == 100


def test_mission_control_and_traces() -> None:
    assessment("INFY")
    board = dashboard()
    assert board["board"] == "Institutional Probability & Confidence Intelligence"
    assert board["principles"]["probability_ne_confidence"] is True
    assert board["principles"]["probabilities_sum_to_100"] is True
    assert board["assessments_executed"] >= 1
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "probability_calculation" in names
    assert "confidence_calculation" in names
    assert "evidence_scoring" in names
    assert "forecast_assessment" in names
