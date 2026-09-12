"""Valuation Consensus — parse / publish / query / Ask provider."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def tmp_store(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("VALUATION_CONSENSUS_ROOT", td)
        from valuation_consensus import store

        store.invalidate_cache()
        yield Path(td)
        store.invalidate_cache()


def test_parse_and_publish_sample_capiq(tmp_store):
    sample = ROOT.parent / "capital_iq_exports" / "capiq_export_460.xlsx"
    if not sample.exists():
        pytest.skip("sample CapIQ export not present")

    from valuation_consensus.production import (
        analytics,
        company_detail,
        health,
        import_preview,
        import_publish,
        query_rows,
    )

    preview = import_preview(
        filename=sample.name,
        content_bytes=sample.read_bytes(),
        actor="test",
    )
    assert preview["ok"] is True
    assert preview["row_count"] > 50
    assert "cmp" in preview["columns_mapped"] or "sector" in preview["columns_mapped"]

    published = import_publish(preview["import_id"], actor="test")
    assert published["ok"] is True
    assert published["row_count"] == preview["row_count"]

    h = health()
    assert h["status"] in {"ok", "degraded"}
    assert h["row_count"] == preview["row_count"]

    a = analytics()
    assert a["total_companies"] == preview["row_count"]
    assert a["sector_cards"]

    q = query_rows(q="abb", page=1, page_size=10, sort="alphabetical")
    assert q["ok"] is True
    assert q["total"] >= 1
    tickers = [r["ticker"] for r in q["items"]]
    assert any("ABB" in t or t for t in tickers)

    detail = company_detail(q["items"][0]["ticker"])
    assert detail["ok"] is True
    assert detail["market_consensus"]["source"] == "capital_iq"
    assert detail["agi_intelligence"]["source"] == "agi"
    assert "ask_agi" in detail["integrations"]


def test_rollback_version(tmp_store):
    from valuation_consensus import store
    from valuation_consensus.production import import_rollback

    v1 = store.publish_rows(
        {
            "AAA": {
                "ticker": "AAA",
                "company_name": "Alpha",
                "cmp": 10,
                "upside": 5,
                "sector": "Banking",
            }
        },
        source_file="v1.xlsx",
        imported_by="test",
    )
    v2 = store.publish_rows(
        {
            "BBB": {
                "ticker": "BBB",
                "company_name": "Beta",
                "cmp": 20,
                "upside": 15,
                "sector": "IT Services",
            }
        },
        source_file="v2.xlsx",
        imported_by="test",
    )
    assert store.load_live()["row_count"] == 1
    assert "BBB" in store.load_live()["rows"]

    rolled = import_rollback(v1["version_id"], actor="test")
    assert rolled["ok"] is True
    live = store.load_live()
    assert "AAA" in live["rows"]
    assert live["source_file"].startswith("rollback:")


def test_kul_provider_surfaces_market_consensus(tmp_store):
    from knowledge_unification.providers.valuation_consensus import ValuationConsensusProvider
    from knowledge_unification.schema import QueryPlan
    from valuation_consensus import store

    store.publish_rows(
        {
            "RELIANCE": {
                "ticker": "RELIANCE",
                "company_name": "Reliance Industries",
                "cmp": 1400,
                "target_price": 1600,
                "upside": 14.28,
                "buy_count": 20,
                "hold_count": 5,
                "sell_count": 1,
                "coverage": 26,
                "sector": "Oil & Gas",
                "industry": "Integrated Oil & Gas",
            }
        },
        source_file="unit.xlsx",
        imported_by="test",
    )

    provider = ValuationConsensusProvider()
    assert provider.health_check() in {"ok", "degraded"}
    plan = QueryPlan(
        question="What is the consensus target for Reliance?",
        question_types=["valuation", "company"],
        ticker_hint="RELIANCE",
        requires_company=True,
    )
    result = provider.consult(plan)
    assert result.ok and not result.empty
    assert "market consensus" in " ".join(result.why).lower()
    assert any(f.get("field") == "consensus_target" for f in result.facts)
    assert result.raw.get("layer") == "market_consensus"
    blob = (result.summary + " " + " ".join(result.why)).lower()
    assert "market consensus" in blob
    assert "not agi advice" in blob or "not agi recommendation" in blob or "distinct from agi" in blob


def test_header_mapping_consensus_columns():
    from valuation_consensus.schema import map_header

    assert map_header("Target Price") == "target_price"
    assert map_header("Buy") == "buy_count"
    assert map_header("Outperform") == "outperform_count"
    assert map_header("% Price Change [1 Year]") == "return_1y"
    assert map_header("Day Close Price [Latest] ($USD, Historical rate)") == "cmp"
    assert map_header("Primary Sector") == "sector"
    # Raw CapIQ Broker Estimates export headers (en-dash often becomes "0")
    assert map_header("Target Price 0 Capital IQ [Latest] (Inr, Historical rate)") == "target_price"
    assert map_header("Target Price High 0 Capital IQ [Latest] (€, Historical rate)") == "target_high"
    assert (
        map_header("# of Analyst Buy (1) Recommendations 0 Capital IQ [Latest]") == "buy_count"
    )
    assert map_header("Potential Upside 0 Capital IQ [Latest] (%)") == "upside"
    assert map_header("Target Price 0 # of Estimates 0 Capital IQ [Latest]") == "coverage"
    assert map_header("Last Price") == "cmp"


def test_broker_estimates_file_maps_and_seeds(tmp_store):
    sample = ROOT.parent / "capital_iq_exports" / "broker_estimates.xlsx"
    if not sample.exists():
        pytest.skip("broker_estimates.xlsx not present")

    from valuation_consensus.production import analytics, query_rows, seed_from_path

    out = seed_from_path(sample, actor="test")
    assert out["ok"] is True
    assert out["row_count"] >= 2000
    a = analytics()
    assert a["total_companies"] >= 2000
    assert a["average_target_upside"] is not None
    q = query_rows(q="RELIANCE", page=1, page_size=5, sort="coverage")
    assert q["total"] >= 1
    assert any(r.get("target_price") is not None for r in q["items"]) or q["total"] >= 1
