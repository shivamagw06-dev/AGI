"""Market Intelligence Engine tests."""

from market_intelligence_engine import aggregation, flows, ingest_flows, opportunities, rotation, summary


def test_opportunity_label_bands():
    assert aggregation._historical_range_status(20) == "Below Historical Range"
    assert aggregation._historical_range_status(50) == "Within Historical Range"
    assert aggregation._historical_range_status(80) == "Above Historical Range"


def test_short_sector_history_is_not_published_as_a_percentile():
    out = aggregation._publishable_history({
        "status": "OK",
        "historical_percentile": 14.0,
        "historical_median": 21.0,
        "observation_count": 184,
    })
    assert out["historical_percentile"] is None
    assert out["status"] == "INSUFFICIENT_HISTORY"
    assert "252" in out["reason"]


def test_full_year_sector_history_remains_publishable():
    out = aggregation._publishable_history({
        "status": "OK",
        "historical_percentile": 14.0,
        "historical_median": 21.0,
        "observation_count": 252,
    })
    assert out["historical_percentile"] == 14.0
    assert out["status"] == "OK"


def test_normalise_upstox_flow():
    rows = ingest_flows.normalise_upstox_flow({
        "date": "2026-08-01",
        "fii": {"buy": 1000, "sell": 800},
        "dii": {"buy": 500, "sell": 600},
    })
    assert len(rows) == 1
    assert rows[0]["fii_net"] == 200.0
    assert rows[0]["dii_net"] == -100.0


def test_detect_opportunities_empty():
    out = opportunities.detect_opportunities({"ok": True, "rows": []})
    assert out["ok"] is False


def test_detect_historical_discount():
    uni = {
        "ok": True,
        "rows": [
            {"symbol": "AAA", "company_name": "A", "sector": "IT", "industry": "Software",
             "pe": 15, "percentile": 8, "source": "warehouse"},
            {"symbol": "BBB", "company_name": "B", "sector": "IT", "industry": "Software",
             "pe": 30, "percentile": 90, "source": "warehouse"},
        ],
    }
    out = opportunities.detect_opportunities(uni, limit_per_kind=2)
    kinds = {c["kind"] for c in out["cards"]}
    assert "historical_discount" in kinds


def test_market_summary_not_empty():
    text = summary.market_summary(
        {"averages": {"pe": 22.5}},
        [{"sector": "IT", "opportunity": "Attractive", "historical_percentile": 25}],
        {"ok": True, "heatmap": "Bullish", "advancing": 800, "declining": 400},
        {"available": False},
    )
    assert "median P/E" in text
    assert "investment advice" in text.lower() or "not investment advice" in text.lower()


def test_sector_table_no_fake_upstox_benchmark():
    """When Upstox coverage is 0%, Sector/Premium must stay empty (not peer median)."""
    uni = {
        "ok": True,
        "rows": [
            {
                "symbol": "AAA",
                "sector": "Industrials",
                "industry_dna": "industrials",
                "pe": 50,
                "sector_median_pe": 50,
                "percentile": 60,
                "provider_coverage": 0,
            },
            {
                "symbol": "BBB",
                "sector": "Industrials",
                "industry_dna": "industrials",
                "pe": 56,
                "sector_median_pe": 56,
                "percentile": 65,
                "provider_coverage": 0,
            },
        ],
    }
    rows = aggregation.sector_table(uni)
    assert len(rows) == 1
    assert rows[0]["current"] is not None
    assert rows[0]["sector_benchmark"] is None
    assert rows[0]["sector_benchmark_source"] is None
    assert rows[0]["premium_pct"] is None
    assert rows[0]["upstox_coverage_pct"] == 0


def test_isin_shape_helper():
    from valuation_ratios.isin_backfill import _valid_isin

    assert _valid_isin("INE002A01018") == "INE002A01018"
    assert _valid_isin("bad") is None


def test_text_confidence_does_not_crash_gateway():
    """valuation_ratios.confidence is TEXT ('high'); must not hit numeric bounds."""
    import os
    import tempfile

    from institutional_warehouse import db, gateway

    root = tempfile.mkdtemp(prefix="wh_conf_")
    os.environ["INSTITUTIONAL_WAREHOUSE_ROOT"] = root
    db.init(force=True)
    result = gateway.write(
        "valuation_ratios",
        [{
            "company_id": "AAA",
            "symbol": "AAA",
            "isin": "INE002A01018",
            "instrument_key": "NSE_EQ|INE002A01018",
            "ratio_name": "pe",
            "company_value": 20.0,
            "sector_value": 18.0,
            "reported_date": "2026-08-04",
            "snapshot_id": "t-conf-1",
            "confidence": "high",
            "dqiv_status": "passed",
            "source": "upstox",
        }],
        source="upstox",
        actor="test",
        detect_conflicts=False,
    )
    assert result.get("ok") is True
    assert result.get("written", 0) >= 1


def test_sector_table_premium_matches_upstox_benchmark(monkeypatch):
    """Premium % must use the Upstox benchmark shown in the Sector column, not HVIE median."""
    def fake_hist(sector, *, current, metric):
        return {
            "historical_percentile": 97,
            "historical_median": 1.54,  # wrong denominator — would yield ~877% premium
            "status": "OK",
            "source": "hvie",
        }

    monkeypatch.setattr(aggregation, "_sector_own_history_percentile", fake_hist)
    uni = {
        "ok": True,
        "rows": [
            {
                "symbol": "AAA",
                "sector": "Industrials",
                "industry_dna": "capital_goods",
                "ev_ebitda": 17.01,
                "sector_median_ev_ebitda": 13.51,
                "percentile": 60,
                "provider_coverage": 1,
            },
            {
                "symbol": "BBB",
                "sector": "Industrials",
                "industry_dna": "capital_goods",
                "ev_ebitda": 17.01,
                "sector_median_ev_ebitda": 13.51,
                "percentile": 65,
                "provider_coverage": 1,
            },
        ],
    }
    rows = aggregation.sector_table(uni)
    assert len(rows) == 1
    assert rows[0]["benchmark_premium_pct"] == 25.9
    assert rows[0]["premium_pct"] == 25.9
    assert rows[0]["premium_basis"] == "upstox_sector_benchmark"
    # Contaminated HVIE median (1.54 vs current 17) must not publish a 1000%+ premium.
    assert rows[0]["historical_premium_pct"] is None


def test_flows_latest_unavailable_not_zero(monkeypatch):
    monkeypatch.setattr(
        "institutional_warehouse.store.all_rows",
        lambda *args, **kwargs: [
            {"date": "2026-08-01", "fii_net": -200, "dii_net": 100},
            {"date": "2026-08-04", "fii_net": None, "dii_net": None, "source": "upstox"},
        ],
    )
    out = flows.institutional_flows()
    assert out["available"] is True
    assert out["latest_values_available"] is False
    assert out["fii_net"] is None
    assert out["dii_net"] is None
    assert out["net_institutional_flow"] is None


def test_rotation_median_caps_outliers():
    sectors = [{"sector": "Materials", "historical_percentile": 50}]
    uni = {
        "rows": [
            {"sector": "Materials", "pe_change_pct": 500},
            {"sector": "Materials", "pe_change_pct": 2},
            {"sector": "Materials", "pe_change_pct": 3},
            {"sector": "Materials", "pe_change_pct": 4},
            {"sector": "Materials", "pe_change_pct": 5},
            {"sector": "Materials", "pe_change_pct": 6},
            {"sector": "Materials", "pe_change_pct": 7},
            {"sector": "Materials", "pe_change_pct": 8},
        ]
    }
    out = rotation.market_rotation(sectors, uni)
    row = out["rows"][0]
    assert row["median_pe_change_pct"] <= rotation.PE_CHANGE_CAP
    assert row["median_pe_change_pct"] == 5.5


def test_research_confidence_varies_by_data_quality():
    opps = {
        "cards": [
            {
                "symbol": "AAA",
                "research_priority": 80,
                "evidence": {"percentile": 10, "pe": 15, "analyst_count": 5},
                "coverage": "warehouse",
                "why": "Rich coverage",
            },
            {
                "symbol": "BBB",
                "research_priority": 55,
                "evidence": {},
                "coverage": "unknown",
                "why": "Sparse coverage",
            },
        ]
    }
    pri = opportunities.research_priorities({}, opps)
    assert pri[0]["confidence"] != pri[1]["confidence"]
    assert pri[0]["confidence"] > pri[1]["confidence"]
    assert pri[1]["confidence"] < 90


def test_constitution_validation_passes_clean_pack():
    from market_intelligence_engine import validation

    pack = {
        "summary": "Institutional context for research prioritisation, not investment advice.",
        "research_priorities": [{"symbol": "AAA", "reason": "Valuation percentile 8%", "selection_reasons": ["Low percentile"]}],
        "sectors": [{"sector": "IT", "premium_pct": 5.0, "premium_basis": "upstox_sector_benchmark"}],
        "breadth": {"universe_definition": "test definition", "provenance": {"source": "test"}},
        "confidence": {"methodology": "test methodology"},
        "market_regime": {"provenance": {"source": "test"}},
        "market_health": {"provenance": {"source": "test"}},
        "market_drivers": {"provenance": {"source": "test"}},
        "flows": {"provenance": {"source": "test"}},
    }
    result = validation.validate_dashboard(pack)
    assert result["publishable"] is True


def test_market_regime_not_risk_on_only():
    from market_intelligence_engine import regime

    out = regime.classify_market_regime(
        breadth={"advancing": 800, "declining": 200, "heatmap": "Strong Bullish", "date": "2026-08-04"},
        flows={"available": True, "trend_5d": 500},
        sectors=[{"sector": "IT", "historical_percentile": 80}, {"sector": "Energy", "historical_percentile": 75}],
        overview={"coverage": {"pct": 70}},
    )
    assert out["regime"] in regime.REGIME_LABELS
    assert out["regime"] not in ("Risk On", "Risk Off")


def test_regime_requires_multi_session_breadth_confirmation():
    from market_intelligence_engine import regime

    out = regime.classify_market_regime(
        breadth={
            "advancing": 700, "declining": 300, "heatmap": "Bullish", "date": "2026-08-04",
            "confirmation": {"sessions": 3, "bullish_sessions": 1, "bearish_sessions": 0,
                             "bullish_confirmed": False, "bearish_confirmed": False},
        },
        flows={"available": False},
        sectors=[],
        overview={"coverage": {"pct": 70}},
    )
    assert out["regime"] == "Transition"
    assert "awaits multi-session confirmation" in out["drivers"][0]


def test_market_health_has_components():
    from market_intelligence_engine.health import market_health_score

    out = market_health_score(
        breadth={"advancing": 400, "declining": 300, "sample_size": 700, "average_return_pct": 0.2},
        flows={"available": True, "trend_5d": 100},
        overview={"coverage": {"pct": 65}, "valuation_date": "2026-08-04"},
        sectors=[{"historical_percentile": 55}],
    )
    assert 0 <= out["overall"] <= 100
    assert "breadth" in out["components"]
    assert out.get("confidence_methodology")
