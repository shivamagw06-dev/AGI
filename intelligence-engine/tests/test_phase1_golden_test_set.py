"""Phase 1 Golden Test Set — 200-stock institutional benchmark universe."""

from __future__ import annotations

import csv
from pathlib import Path

from institutional_evaluation_lab.datasets.catalog import catalog_stats, load_suite
from institutional_evaluation_lab.production import catalog, phase1_golden_universe
from knowledge_factory.phase1_golden_test_set import (
    PHASE1_GOLDEN_200,
    PHASE1_TARGET_N,
    by_bucket,
    lookup,
    summary,
    tickers,
    validate_universe,
)


def test_phase1_composition_exact():
    from knowledge_factory.phase1_golden_test_set import (
        FROZEN,
        FROZEN_COMPOSITION_SHA256,
        GOLDEN_UNIVERSE_VERSION,
        composition_fingerprint,
    )

    s = summary()
    assert s["n"] == PHASE1_TARGET_N == 200
    assert s["meets_target"] is True
    assert s["golden_universe_version"] == GOLDEN_UNIVERSE_VERSION == "v1.0"
    assert s["frozen"] is True
    assert s["bucket_counts"] == {
        "nifty_50": 50,
        "nifty_next_50": 50,
        "midcap": 50,
        "smallcap": 25,
        "special_situation": 25,
    }
    v = validate_universe()
    assert v["valid"] is True
    assert v["frozen_ok"] is True
    assert FROZEN is True
    assert composition_fingerprint() == FROZEN_COMPOSITION_SHA256
    assert not v["duplicates"]
    assert not v["overlaps"]


def test_no_cross_bucket_overlap():
    buckets = by_bucket()
    sets = {k: {r["ticker"] for r in rows} for k, rows in buckets.items()}
    assert len(sets["nifty_50"] & sets["nifty_next_50"]) == 0
    assert len(sets["nifty_50"] & sets["midcap"]) == 0
    assert len(sets["nifty_next_50"] & sets["midcap"]) == 0
    assert len(sets["midcap"] & sets["smallcap"]) == 0
    assert len(sets["special_situation"] & sets["nifty_50"]) == 0
    assert len(sets["special_situation"] & sets["nifty_next_50"]) == 0
    assert len(sets["special_situation"] & sets["midcap"]) == 0
    assert len(sets["special_situation"] & sets["smallcap"]) == 0


def test_tickers_match_nifty500_membership():
    csv_path = Path("/workspace/Nifty500.csv")
    assert csv_path.exists()
    nifty500 = {r["Symbol"].upper() for r in csv.DictReader(csv_path.open())}
    missing = [t for t in PHASE1_GOLDEN_200 if t not in nifty500]
    # Allow empty: every golden ticker should be in the Nifty 500 dump
    assert missing == [], missing


def test_special_situations_have_profiles():
    special = by_bucket()["special_situation"]
    assert len(special) == 25
    for row in special:
        assert row["profile"]
        assert row["market_cap_bucket"] == "special"
    assert lookup("ZOMATO") is not None  # alias → ETERNAL
    assert lookup("ZOMATO")["ticker"] == "ETERNAL"
    assert "IDEA" in tickers(bucket="special_situation")
    assert "PAYTM" in tickers(bucket="special_situation")


def test_index_symbol_renames_keep_aliases():
    assert lookup("TATAMOTORS")["ticker"] == "TMPV"
    assert lookup("LTIM")["ticker"] == "LTM"
    assert "TMPV" in tickers(bucket="nifty_50")
    assert "LTM" in tickers(bucket="nifty_next_50")


def test_sector_breadth():
    s = summary()
    assert s["sector_count"] >= 12
    # Large-cap buckets should include banking + IT
    n50 = {r["ticker"] for r in by_bucket()["nifty_50"]}
    assert {"HDFCBANK", "TCS", "RELIANCE", "INFY"}.issubset(n50)


def test_iel_catalog_and_api_board():
    rows = load_suite("phase1_golden_200")
    assert len(rows) == 200
    stats = catalog_stats()
    assert stats["phase1_golden_200"] == 200
    assert stats["phase1_golden_valid"] is True
    board = phase1_golden_universe()
    assert board["valid"] is True
    cat = catalog(suite="phase1_golden_200", limit=10)
    assert cat["kind"] == "universe"
    assert len(cat["companies"]) == 10
