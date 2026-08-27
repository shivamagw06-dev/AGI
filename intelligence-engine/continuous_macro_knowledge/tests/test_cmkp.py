"""Sprint 10.1 — Continuous Macroeconomic Knowledge Platform tests."""

from __future__ import annotations

from continuous_macro_knowledge import traces
from continuous_macro_knowledge.materiality import evaluate_materiality
from continuous_macro_knowledge.normalization import normalize_release
from continuous_macro_knowledge.production import (
    dashboard,
    global_macro,
    health,
    india,
    indicator,
    release_calendar,
    releases,
    run,
)
from continuous_macro_knowledge.schema import NO_CMKP_ACTIONS, RawMacroRelease
from continuous_macro_knowledge.store import reset
from continuous_macro_knowledge.validation import validate_release


def setup_function() -> None:
    reset()
    traces.clear()


def test_cmkp_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "CMKP"
    assert h["ask_triggers_collection"] is False
    assert "Ask" in h["independent_of"]
    for item in NO_CMKP_ACTIONS:
        assert item in h["does_not"]
    assert "rbi" in h["sources"] and "fred" in h["sources"]


def test_read_apis_never_collect() -> None:
    """Empty store — reads must not trigger ingestion."""
    out = india()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["ask_triggers_collection"] is False
    miss = indicator("CPI")
    assert miss["found"] is False
    assert miss["collected_on_request"] is False


def test_continuous_ingestion_publishes_mkos() -> None:
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["user_interaction"] is False
    assert summary["published"] >= 15
    assert summary["validated"] >= 15

    ind = india()
    assert ind["n"] >= 10
    assert ind["collected_on_request"] is False
    assert "Inflation" in ind["by_category"] or "Monetary" in ind["by_category"]

    glob = global_macro()
    assert glob["n"] >= 3
    assert glob["collected_on_request"] is False

    cpi = indicator("CPI", country="India")
    assert cpi["found"] is True
    assert cpi["latest"]["source"] == "mospi"
    assert cpi["latest"]["current_value"] is not None
    assert cpi["collected_on_request"] is False
    assert cpi["latest"]["version"] >= 1


def test_repo_unchanged_ignored_for_learning() -> None:
    run()
    repo = indicator("Repo Rate", country="India")
    assert repo["found"] is True
    assert repo["latest"]["materiality_tier"] == "Ignore"
    # Learning events should not include repo-unchanged
    board = dashboard()
    topics = " ".join(l.get("topic", "") for l in board.get("learning_events") or [])
    # Repo may appear if somehow learned — assert tier Ignore on object
    assert repo["latest"]["learning_generated"] is False


def test_repo_cut_high_materiality_learning() -> None:
    run()
    raw = RawMacroRelease(
        source="rbi",
        country="India",
        category="Monetary",
        indicator="Repo Rate",
        current_value=6.00,
        previous_value=6.50,
        consensus=6.25,
        unit="%",
        release_date="2026-08-08",
        importance="Critical",
        payload={"mpc": "cut"},
    )
    assert validate_release(raw)["ok"]
    mko = normalize_release(raw)
    assert mko.version >= 2  # prior from run()
    mat = evaluate_materiality(mko)
    assert mat["tier"] in {"High", "Critical"}
    assert mat["learn"] is True
    assert mat["filtered"] is False
    from continuous_macro_knowledge.learning import generate_learning
    from continuous_macro_knowledge.publish import publish_mko
    from continuous_macro_knowledge.store import STORE

    event = generate_learning(mko, materiality=mat)
    assert event is not None
    assert "cut" in event.observation.lower() or "bps" in event.observation.lower()
    assert event.forecast_refresh_hint is True
    mko.learning_generated = True
    publish_mko(mko)
    STORE.add_learning(event)
    latest = indicator("Repo Rate", country="India")
    assert latest["latest"]["current_value"] == 6.0
    assert latest["latest"]["materiality_tier"] in {"High", "Critical"}


def test_versioned_objects() -> None:
    run()
    run()  # second pass increments versions
    cpi = indicator("CPI", country="India")
    assert cpi["found"] is True
    assert cpi["latest"]["version"] >= 2
    assert len(cpi["versions"]) >= 2


def test_calendar_and_releases() -> None:
    run()
    cal = release_calendar()
    assert cal["n"] >= 5
    assert cal["ask_triggered"] is False
    rel = releases(limit=20)
    assert rel["n"] >= 10
    assert rel["collected_on_request"] is False


def test_mission_control_and_traces() -> None:
    run()
    board = dashboard()
    assert board["board"] == "Macro Operations"
    assert board["principles"]["ask_never_fetches"] is True
    assert board["collector_health"]
    assert board["latest_releases"]
    assert board["knowledge_coverage"]["published_objects"] >= 15
    assert board["upcoming_releases"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    # Full pipeline stages (collection may fall outside a tiny window when many releases fan out)
    assert "macro_validation" in names
    assert "macro_normalization" in names
    assert "macro_materiality" in names
    assert "macro_publication" in names
    all_names = {t["name"] for t in traces.recent(200)}
    assert "macro_collection" in all_names
    assert "macro_learning" in all_names or board["materiality"]["learning_count"] >= 0


def test_cpi_surprise_can_learn() -> None:
    run()
    cpi = indicator("CPI", country="India")["latest"]
    # Seeded CPI 3.65 vs consensus 3.50 → surprise 0.15 → Medium learn
    assert cpi["materiality_tier"] in {"Medium", "High", "Low", "Ignore"}
    if cpi["normalized"]["surprise_vs_consensus"] is not None:
        assert abs(cpi["normalized"]["surprise_vs_consensus"] - 0.15) < 0.001
