

# --------------------------------------------------------------------------
# Empty payloads
#
# POST {} to the ingest route used to write a row: today's date, the default
# segment, every figure null. It then sat at the top of institutional_flow
# making the feed look current while carrying nothing - and the freshness
# monitor read it as fresh, which is worse than an obviously stale table.
# Found by doing exactly that with a test POST.
# --------------------------------------------------------------------------


def test_an_empty_payload_writes_nothing():
    from market_intelligence_engine.ingest_flows import normalise_upstox_flow

    assert normalise_upstox_flow({}) == []
    assert normalise_upstox_flow({"fii": {}, "dii": {}}) == []
    assert normalise_upstox_flow({"date": "2026-08-23"}) == []


def test_a_payload_with_a_figure_still_writes():
    from market_intelligence_engine.ingest_flows import normalise_upstox_flow

    rows = normalise_upstox_flow({
        "date": "2026-08-21",
        "fii": {"buy_amount": 100.0, "sell_amount": 60.0},
        "dii": {"buy_amount": 50.0, "sell_amount": 40.0},
    })
    assert len(rows) == 1
    assert rows[0]["fii_net"] == 40.0 and rows[0]["dii_net"] == 10.0


def test_one_side_of_the_trade_is_enough():
    """A day where only DII reported is real data, not an empty payload."""
    from market_intelligence_engine.ingest_flows import normalise_upstox_flow

    rows = normalise_upstox_flow({"date": "2026-08-21", "dii": {"net": 120.5}})
    assert len(rows) == 1
    assert rows[0]["dii_net"] == 120.5


def test_the_observations_path_is_unaffected():
    """The guard must not block the shape the fetcher actually produces."""
    from market_intelligence_engine.ingest_flows import normalise_upstox_flow

    rows = normalise_upstox_flow({"observations": [{
        "observation_date": "2026-08-21", "segment": "NSE_EQ|CASH",
        "participant": "FII", "buy_amount": 10.0, "sell_amount": 5.0,
    }]})
    assert len(rows) == 1 and rows[0]["fii_net"] == 5.0
