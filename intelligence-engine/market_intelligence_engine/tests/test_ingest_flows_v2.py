from market_intelligence_engine.ingest_flows import normalise_upstox_flow
def test_normalises_segment_observations_without_collapsing_derivatives():
    rows = normalise_upstox_flow({"observations": [{"participant": "FII", "segment": "NSE_FO|INDEX_FUTURES", "interval": "1D", "observation_date": "2026-08-07", "buy_amount": 100, "sell_amount": 80, "long_contracts": 40}, {"participant": "DII", "segment": "NSE_EQ|CASH", "interval": "1D", "observation_date": "2026-08-07", "buy_amount": 120, "sell_amount": 90}]})
    assert len(rows) == 2
    derivative = next(row for row in rows if row["segment"] == "NSE_FO|INDEX_FUTURES")
    cash = next(row for row in rows if row["segment"] == "NSE_EQ|CASH")
    assert derivative["fii_net"] == 20 and derivative["fii_long_contracts"] == 40
    assert cash["dii_net"] == 30
