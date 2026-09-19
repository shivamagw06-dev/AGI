"""Sprint 9.1 — Institutional Forecast Intelligence tests."""

from __future__ import annotations

from institutional_forecast_intelligence.completeness import assess_completeness
from institutional_forecast_intelligence.production import (
    bundle,
    company,
    dashboard,
    health,
    macro,
    market,
    sector,
    theme,
)
from institutional_forecast_intelligence.schema import CompletenessStatus, NO_IFI_JUDGMENT


def test_ifi_health_and_non_judgment() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "IFI"
    assert h["providers_queried_always"] == []
    for item in NO_IFI_JUDGMENT:
        assert item in h["does_not"]


def test_company_forecast_bundle_infosys() -> None:
    out = company("INFY")
    assert out["providers_queried"] == []
    assert out["scope"] == "company"
    assert out["entity"] == "INFY"
    assert out["chooses_scenario"] is False
    assert out["assigns_probabilities"] is False
    assert out["is_price_prediction"] is False
    assert out["is_recommendation"] is False
    assert out["current_knowledge"]["name"] == "Infosys"
    assert out["historical_intelligence"]
    assert out["historical_analogues"]
    assert out["relationship_intelligence"]
    assert out["research_intelligence"]
    assert out["monitoring_events"]
    assert out["catalysts"]
    assert out["risks"]
    assert out["supporting_evidence"]
    assert "Revenue Outlook" in out["outlook_dimensions"]
    # Pattern intelligence deferred (8.5) → reduced completeness, not invented
    assert out["pattern_intelligence"].get("deferred") is True
    assert "pattern_intelligence" in out["completeness"]["missing_evidence"]
    assert out["completeness"]["overall"] in {
        CompletenessStatus.PARTIAL.value,
        CompletenessStatus.COMPLETE.value,
        CompletenessStatus.SPARSE.value,
    }
    # Must not smuggle Bull/Base/Bear selection
    blob = str(out).lower()
    assert "bull case" not in blob
    assert out["provenance"]["scenario_selection"] is False


def test_sector_market_macro_theme_bundles() -> None:
    s = sector("information_technology")
    assert s["providers_queried"] == []
    assert s["scope"] == "sector"
    assert s["outlook_dimensions"]

    mkt = market()
    assert mkt["scope"] == "market"
    assert mkt["market_intelligence"]["market"] == "NIFTY"

    mac = macro()
    assert mac["scope"] == "macro"
    assert mac["macro_intelligence"]["region"] == "India"
    assert mac["historical_analogues"]

    th = theme("artificial_intelligence")
    assert th["scope"] == "theme"
    assert th["research_intelligence"]


def test_bundle_api_and_dashboard() -> None:
    b = bundle(scope="company", entity="HDFCBANK", question="Prepare forecast context for rate cuts")
    assert b["entity"] == "HDFCBANK"
    assert b["providers_queried"] == []
    assert any(
        "RBI" in str(r.get("source") or "") or "rbi" in str(r.get("source") or "").lower()
        for r in b["relationship_intelligence"]
    )

    company("INFY")
    board = dashboard()
    assert board["board"] == "Institutional Forecast Intelligence"
    assert board["principles"]["no_bull_base_bear_selection"] is True
    assert board["principles"]["no_live_providers_on_forecast_path"] is True
    assert board["forecast_bundle_generations"] >= 1
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "forecast_bundle_generation" in names
    assert "forecast_knowledge_retrieval" in names
    assert "forecast_context_preparation" in names
    assert "forecast_publication" in names


def test_completeness_does_not_invent_missing() -> None:
    c = assess_completeness(
        {
            "current_knowledge": {"ticker": "X"},
            "historical_intelligence": {},
            "pattern_intelligence": {"deferred": True},
        }
    )
    assert "pattern_intelligence" in c.missing_evidence
    assert c.pattern_intelligence == CompletenessStatus.MISSING
    assert c.overall != CompletenessStatus.COMPLETE


def test_no_live_provider_keys_in_bundle() -> None:
    out = company("TCS")
    assert out["providers_queried"] == []
    assert "yahoo" not in str(out.get("provenance")).lower()
    assert out["provenance"]["providers_hidden"] is True
