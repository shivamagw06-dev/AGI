"""Sprint 9.2 — Institutional Scenario Intelligence tests."""

from __future__ import annotations

from institutional_forecast_intelligence.production import company as ifi_company
from institutional_scenario_intelligence.production import (
    company,
    dashboard,
    health,
    macro,
    market,
    report,
    sector,
)
from institutional_scenario_intelligence.schema import NO_ISI_JUDGMENT
from institutional_scenario_intelligence.validation import validate_report
from institutional_scenario_intelligence.schema import ScenarioReport, InstitutionalScenario, ScenarioType, ScenarioScope


def test_isi_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "ISI"
    assert h["providers_queried_always"] == []
    assert "assign_probabilities" in h["does_not"]
    assert "recommend_buy_sell" in h["does_not"]


def test_infosys_bull_base_bear_from_ifi_bundle() -> None:
    """Every Forecast Bundle produces evidence-backed Bull / Base / Bear."""
    out = company("INFY")
    assert out["providers_queried"] == []
    assert out["scope"] == "company"
    assert out["entity"] == "INFY"
    assert out["forecast_bundle_id"]
    assert out["chooses_single_future"] is False
    assert out["assigns_probabilities"] is False
    assert out["is_price_prediction"] is False
    assert out["is_recommendation"] is False
    assert set(out["bull_base_bear_coverage"]) == {"Base", "Bear", "Bull"}

    by_type = {s["type"]: s for s in out["scenarios"]}
    assert "Enterprise AI spending accelerates." in by_type["Bull"]["narrative"]
    assert "Revenue grows near guidance." in by_type["Base"]["narrative"]
    assert "US enterprise spending weakens." in by_type["Bear"]["narrative"]

    for s in out["scenarios"]:
        assert s["supporting_evidence"]
        assert s["probability"] is None
        assert s["is_recommendation"] is False
        assert s["drivers"]
        assert s["catalysts"] is not None
        assert s["risks"] is not None

    # Contradiction analysis preserves both margin paths
    dims = {c.get("dimension") for c in out["contradictions"]}
    assert "Margins" in dims
    assert out["comparison"]["why_all_remain_plausible"]
    assert out["comparison"]["conflicting_drivers"]


def test_consumes_explicit_forecast_bundle() -> None:
    fb = ifi_company("HDFCBANK")
    out = report(scope="company", forecast_bundle=fb)
    assert out["entity"] == "HDFCBANK"
    assert out["forecast_bundle_id"] == fb["bundle_id"]
    assert len(out["scenarios"]) == 3
    # Rate-cut relationship should surface on bull catalysts or evidence
    blob = str(out).lower()
    assert "rbi" in blob or "rate" in blob


def test_sector_market_macro_reports() -> None:
    s = sector("information_technology")
    assert s["providers_queried"] == []
    assert set(s["bull_base_bear_coverage"]) == {"Base", "Bear", "Bull"}

    m = market()
    assert m["scope"] == "market"
    assert len(m["scenarios"]) == 3

    mac = macro()
    assert mac["scope"] == "macro"
    assert mac["contradictions"]


def test_no_buy_sell_or_target_price() -> None:
    out = company("TCS")
    # Inspect scenario content only — does_not list intentionally names forbidden actions
    content = {
        "scenarios": out["scenarios"],
        "comparison": out["comparison"],
        "investment_thesis": out.get("investment_thesis"),
    }
    blob = str(content).lower()
    for banned in ("buy", "sell", "target price", "price target", "accumulate"):
        assert banned not in blob
    for item in NO_ISI_JUDGMENT:
        assert item in out["does_not"]


def test_validation_requires_evidence() -> None:
    bad = InstitutionalScenario(
        type=ScenarioType.BULL,
        narrative=["Upside"],
        supporting_evidence=[],
    )
    from institutional_scenario_intelligence.validation import validate_scenario

    assert "supporting_evidence_required" in validate_scenario(bad)

    report_obj = ScenarioReport(
        scope=ScenarioScope.COMPANY,
        entity="INFY",
        scenarios=[
            InstitutionalScenario(
                type=ScenarioType.BULL,
                narrative=["AI accelerates"],
                supporting_evidence=[{"kind": "test", "summary": "ok"}],
            ),
            InstitutionalScenario(
                type=ScenarioType.BASE,
                narrative=["Stable"],
                supporting_evidence=[{"kind": "test", "summary": "ok"}],
            ),
            InstitutionalScenario(
                type=ScenarioType.BEAR,
                narrative=["Weak demand"],
                supporting_evidence=[{"kind": "test", "summary": "ok"}],
            ),
        ],
    )
    assert validate_report(report_obj) == []


def test_mission_control_dashboard() -> None:
    company("INFY")
    board = dashboard()
    assert board["board"] == "Institutional Scenario Intelligence"
    assert board["principles"]["contradictions_preserved"] is True
    assert board["principles"]["no_probabilities_until_pci"] is True
    assert board["active_scenario_reports"] >= 1
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "scenario_generation" in names
    assert "scenario_comparison" in names
    assert "scenario_validation" in names
    assert "scenario_publication" in names
