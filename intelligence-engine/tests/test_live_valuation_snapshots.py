from valuation_intelligence.live_snapshots import (
    build_fundamental_vintage, calculate_state, process_tick, snapshot_decision,
)


def _fact(metric, value, period="2026-06-30", publication="2026-07-18", source_id=None):
    return {"canonical_metric": metric, "value": value, "period_end": period,
            "publication_date": publication, "available_at": publication,
            "source_id": source_id or metric}


def _vintage():
    return build_fundamental_vintage([
        _fact("shares_outstanding_million", 100), _fact("eps", 10),
        _fact("book_value_per_share", 80), _fact("tangible_book_value_per_share", 70),
        _fact("ebitda", 500), _fact("revenue", 2000), _fact("free_cash_flow", 200),
        _fact("total_debt", 300), _fact("cash_and_equivalents", 100), _fact("roe", 15),
    ], price_as_of="2026-08-16T10:00:00Z")


def test_calculates_pit_state_without_touching_annual_history():
    result = calculate_state(quote={"symbol": "AAA", "last": 120, "volume": 10_000,
                                    "price_as_of": "2026-08-16T10:00:00Z", "provider_id": "upstox"},
                             vintage=_vintage(), calculated_at="2026-08-16T10:00:01Z")
    row = result["row"]
    assert row["market_cap"] == 12000
    assert row["pe"] == 12
    assert row["pb"] == 1.5
    assert row["enterprise_value"] == 12200
    assert row["fundamental_publication_date"] == "2026-07-18"


def test_rejects_lookahead_financial_vintage():
    vintage = {**_vintage(), "fundamental_publication_date": "2026-08-17"}
    result = calculate_state(quote={"symbol": "AAA", "last": 120,
                                    "price_as_of": "2026-08-16T10:00:00Z"}, vintage=vintage)
    assert result["status"] == "PIT_INVALID"


def test_rejects_unattributed_price_timestamp():
    result = calculate_state(quote={"symbol": "AAA", "last": 120}, vintage=_vintage())
    assert result["status"] == "DATA_REQUIRED"
    assert "price_as_of" in result["missing"]


def test_snapshot_rules_cover_interval_move_and_vintage_change():
    previous = {"price": 100, "calculation_timestamp": "2026-08-16T10:00:00Z", "fundamental_vintage_id": "v1"}
    assert snapshot_decision({"price": 100.5, "calculation_timestamp": "2026-08-16T10:05:00Z", "fundamental_vintage_id": "v1"}, previous)["persist"] is False
    assert snapshot_decision({"price": 101.1, "calculation_timestamp": "2026-08-16T10:05:00Z", "fundamental_vintage_id": "v1"}, previous)["reason"] == "MATERIAL_PRICE_MOVE"
    assert snapshot_decision({"price": 100.5, "calculation_timestamp": "2026-08-16T10:15:00Z", "fundamental_vintage_id": "v1"}, previous)["reason"] == "INTERVAL_15M"
    assert snapshot_decision({"price": 100, "calculation_timestamp": "2026-08-16T10:01:00Z", "fundamental_vintage_id": "v2"}, previous)["reason"] == "FINANCIAL_EVENT"


def test_process_tick_writes_live_and_snapshot_separately():
    calls = []
    def writer(tab, rows, **kwargs):
        calls.append((tab, rows[0], kwargs)); return {"ok": True, "written": 1}
    result = process_tick(quote={"symbol": "AAA", "last": 120, "price_as_of": "2026-08-16T10:00:00Z"},
                          vintage=_vintage(), previous=None, writer=writer,
                          calculated_at="2026-08-16T10:00:01Z")
    assert [call[0] for call in calls] == ["live_valuation_state", "valuation_snapshots"]
    assert result["decision"]["reason"] == "INITIAL"
