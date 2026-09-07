"""Sprint 11.2 — Historical Sector Intelligence Platform tests."""

from __future__ import annotations

from historical_sector_intelligence import traces
from historical_sector_intelligence.normalization import normalize_observation
from historical_sector_intelligence.production import (
    dashboard,
    events,
    health,
    history,
    run,
    search,
    sector,
    timeline,
)
from historical_sector_intelligence.schema import (
    NO_HSIP_ACTIONS,
    STORAGE_NAMESPACES,
    RawHistoricalSectorObservation,
)
from historical_sector_intelligence.store import STORE, reset
from continuous_sector_knowledge.schema import SECTOR_UNIVERSE
from historical_macro_intelligence.production import run as hmip_run
from historical_macro_intelligence.store import reset as hmip_reset


def setup_function() -> None:
    reset()
    traces.clear()
    hmip_reset()


def test_hsip_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "HSIP"
    assert h["phase"] == "11.2"
    assert h["immutable_store"] is True
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["sector_count"] == len(SECTOR_UNIVERSE)
    for item in NO_HSIP_ACTIONS:
        assert item in h["does_not"]
    for ns in STORAGE_NAMESPACES:
        assert ns in h["namespaces"]


def test_read_never_collects() -> None:
    out = history()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    miss = sector("banking")
    assert miss["found"] is False
    assert miss["collected_on_request"] is False


def test_ingestion_builds_immutable_series_and_timelines() -> None:
    hmip_run()  # soft provenance tip
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["immutable_store"] is True
    assert summary["providers_queried"] == []
    assert summary["published_total"] >= 200
    assert summary["timelines"] >= len(SECTOR_UNIVERSE)

    it = sector("it_services")
    assert it["found"] is True
    assert it["providers_queried"] == []
    assert it["timeline"] is not None
    assert it["timeline"]["completeness_pct"] >= 50
    events_labels = [n.get("event") for n in it["timeline"]["nodes"] if n.get("event")]
    assert any("COVID" in (e or "") or "AI" in (e or "") or "GFC" in (e or "") for e in events_labels)


def test_it_timeline_regime_anchors() -> None:
    run()
    tl = timeline(sector="IT Services", indicator="Revenue Growth")
    assert tl["n"] >= 1
    nodes = tl["timelines"][0]["nodes"]
    labels = {n["year"]: n.get("event") for n in nodes}
    assert labels.get(2008) == "GFC"
    assert "AI" in (labels.get(2023) or "")
    assert labels.get(2000) == "Dot-com Recovery"


def test_immutable_no_overwrite_on_rerun() -> None:
    first = run()
    n1 = first["published_total"]
    second = run()
    assert second["published_total"] == n1
    assert second["duplicate_checksums_skipped"] >= n1
    assert second["published_new"] == 0


def test_revision_appends_new_version() -> None:
    run()
    raw = RawHistoricalSectorObservation(
        source="company_history",
        sector_key="it_services",
        sector_label="IT Services",
        category="Growth",
        indicator="Revenue Growth",
        value=9.5,  # revised vs seeded FY2025 8.0
        period="FY2025",
        unit="% yoy",
        publication_date="2025-03-31",
    )
    prior_n = STORE.coverage()["total_observations"]
    hsko = normalize_observation(raw, revision_note="fy25_revision")
    STORE.append(hsko)
    assert STORE.coverage()["total_observations"] == prior_n + 1
    versions = STORE.versions("it_services", "Revenue Growth", "FY2025")
    assert len(versions) >= 2
    assert versions[-1].version >= 2


def test_search_events_banking() -> None:
    run()
    bank = sector("Banking")
    assert bank["found"] is True
    assert bank["n"] >= 5
    ev = events(sector="banking")
    assert ev["n"] >= 1
    assert any("COVID" in str(e.get("events")) or "GFC" in str(e.get("events")) for e in ev["events"])
    hit = search(q="BS-VI", sector="auto")
    assert hit["n"] >= 1
    pe = search(q="inflation", category="Events")
    assert pe["collected_on_request"] is False


def test_namespaces_and_dashboard() -> None:
    run()
    cov = STORE.coverage()
    assert cov["by_namespace"]["historical_sector_growth"] >= 1
    assert cov["by_namespace"]["historical_sector_valuation"] >= 1
    assert cov["unique_sectors"] == len(SECTOR_UNIVERSE)
    board = dashboard()
    assert board["board"] == "Historical Sector"
    assert board["principles"]["immutable_store"] is True
    assert board["historical_coverage"]["total_observations"] >= 200
    assert board["timeline_completeness"]["average_completeness_pct"] > 0
    assert board["valuation_history"] is not None
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "historical_sector_collection" in names
    assert "historical_sector_validation" in names
    assert "historical_sector_normalization" in names
    assert "historical_sector_publication" in names
