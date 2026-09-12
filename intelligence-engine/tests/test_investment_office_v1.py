"""Investment Office V1 — executive operating cockpit (aggregate only)."""

from __future__ import annotations

from investment_office.production import dashboard, health, package_for_ask_agi, quality_gates, reset_for_tests
from investment_office.schema import IO_VERSION


def setup_function() -> None:
    reset_for_tests()


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == IO_VERSION
    assert h["not_an_engine"] is True
    assert h["flags"]["INVESTMENT_OFFICE"] is True


def test_desk_not_empty():
    desk = dashboard(
        ui_home={
            "hero": {
                "house_view": "Selective constructive",
                "market_regime": "Cautious Constructive",
                "risk_level": "Medium",
                "research_published_today": 1,
            },
            "morning_intelligence": {"greeting_line": "IO believes today.", "cards": []},
            "calendar": [{"title": "RBI"}],
            "feeds": {"latest_research": [{"title": "Note"}]},
        }
    )
    assert desk["enabled"] is True
    assert desk["empty_state"] is False
    assert desk["morning_executive_brief"]["market_regime"]
    assert len(desk["todays_research_queue"]) >= 1
    assert desk["executive_copilot"]["prompts"]
    assert desk["system_health"]["ioc_only"] is True
    assert len(desk["notifications"]) >= 1


def test_ask_agi_package():
    dashboard(ui_home={"hero": {"market_regime": "Risk-on", "risk_level": "Low"}})
    pkg = package_for_ask_agi("What deserves attention?", ticker="HDFCBANK")
    assert pkg.get("enabled") is True
    assert pkg.get("ask_agi_hints")


def test_quality_gates_pass():
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["criteria"]["ioc_system_health"] is True
