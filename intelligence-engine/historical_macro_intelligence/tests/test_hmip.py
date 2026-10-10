"""Sprint 10.2 — Historical Macroeconomic Intelligence Platform tests."""

from __future__ import annotations

from historical_macro_intelligence import traces
from historical_macro_intelligence.production import (
    country,
    dashboard,
    health,
    history,
    indicator,
    run,
    search,
    timeline,
)
from historical_macro_intelligence.schema import NO_HMIP_ACTIONS, RawHistoricalObservation
from historical_macro_intelligence.normalization import normalize_observation
from historical_macro_intelligence.store import STORE, reset
from historical_macro_intelligence.validation import validate_observation


def setup_function() -> None:
    reset()
    traces.clear()


def test_hmip_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "HMIP"
    assert h["immutable_store"] is True
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    for item in NO_HMIP_ACTIONS:
        assert item in h["does_not"]


def test_read_never_collects() -> None:
    out = history()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["providers_queried"] == []
    miss = indicator("Repo Rate")
    assert miss["found"] is False
    assert miss["collected_on_request"] is False


def test_ingestion_builds_immutable_series_and_timelines() -> None:
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["immutable_store"] is True
    assert summary["published_total"] >= 40
    assert summary["timelines"] >= 10

    repo = indicator("Repo Rate", country="India")
    assert repo["found"] is True
    assert repo["providers_queried"] == []
    assert repo["n"] >= 8
    periods = [r["period"] for r in repo["series"]]
    assert "1998" in periods and "2020" in periods and "2025" in periods
    assert repo["timeline"] is not None
    assert repo["timeline"]["completeness_pct"] >= 80
    events = [n.get("event") for n in repo["timeline"]["nodes"] if n.get("event")]
    assert any("COVID" in (e or "") for e in events)


def test_gdp_timeline_regime_anchors() -> None:
    run()
    gdp = indicator("GDP", country="India")
    assert gdp["found"] is True
    tl = gdp["timeline"]
    labels = {n["year"]: n.get("event") for n in tl["nodes"]}
    assert labels.get(2008) == "GFC"
    assert labels.get(2020) == "COVID"
    assert labels.get(2021) == "Recovery"


def test_immutable_no_overwrite_on_rerun() -> None:
    first = run()
    n1 = first["published_total"]
    second = run()
    assert second["published_total"] == n1
    assert second["duplicate_checksums_skipped"] >= n1
    assert second["published_new"] == 0


def test_revision_appends_new_version() -> None:
    run()
    raw = RawHistoricalObservation(
        source="mospi",
        country="India",
        category="Inflation",
        indicator="CPI",
        value=3.80,  # revised vs seeded 3.7 for 2025
        period="2025",
        previous=5.4,
        unit="% yoy",
        publication_date="2026-01-15",
    )
    assert validate_observation(raw)["ok"]
    hmko = normalize_observation(raw, revision_note="official_restatement")
    assert hmko.version >= 2
    prior_n = STORE.coverage()["total_observations"]
    STORE.append(hmko)
    assert STORE.coverage()["total_observations"] == prior_n + 1
    versions = STORE.versions("India", "CPI", "2025")
    assert len(versions) >= 2
    assert versions[-1].value == 3.80
    assert versions[-1].immutable is True


def test_country_and_search_and_timeline_apis() -> None:
    run()
    ind = country("India")
    assert ind["n"] >= 20
    assert ind["providers_queried"] == []
    assert "Repo Rate" in ind["by_indicator"]

    us = country("United States")
    assert us["n"] >= 5
    assert "Federal Funds Rate" in us["by_indicator"]

    hits = search(q="inflation", country="India")
    assert hits["n"] >= 1
    assert hits["collected_on_request"] is False

    tls = timeline()
    assert tls["n"] >= 5
    repo_tl = timeline(indicator="Repo Rate", country="India")
    assert repo_tl["n"] == 1
    assert repo_tl["timelines"][0]["indicator"] == "Repo Rate"


def test_namespaces_and_dashboard() -> None:
    run()
    hist = history(limit=50)
    assert hist["coverage"]["by_namespace"]["historical_rates"] >= 1
    assert hist["coverage"]["by_namespace"]["historical_inflation"] >= 1
    assert hist["coverage"]["year_span"][0] <= 2000

    board = dashboard()
    assert board["board"] == "Historical Macro"
    assert board["principles"]["never_overwrite"] is True
    assert board["historical_coverage"]["total_observations"] >= 40
    assert board["timeline_completeness"]["average_completeness_pct"] > 0
    # Per-observation validation/normalization/publication can push collection out of a small window
    all_names = {t["name"] for t in traces.recent(600)}
    assert "historical_macro_validation" in all_names
    assert "historical_macro_normalization" in all_names
    assert "historical_macro_publication" in all_names
    assert STORE.recent_runs(1)  # collection run recorded
    assert STORE.recent_runs(1)[0].get("collected") >= 40
    # Trigger retrieval trace
    indicator("CPI")
    assert "historical_macro_retrieval" in {t["name"] for t in traces.recent(600)}
