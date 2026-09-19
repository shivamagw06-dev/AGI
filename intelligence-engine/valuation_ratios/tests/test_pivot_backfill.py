"""Repairing a day whose ratios were collected before the sweep pivoted them.

The sweep now writes historical_valuation as it goes, but every day swept
before that has its ratios in valuation_ratios and nothing in the table the
sector desk reads. Re-sweeping cannot fix it: checkpoints are per day, so a
resumed sweep finds an empty queue, and an unresumed one restarts at the top
of the universe and rewrites the same first 300 companies - which is exactly
what happened when this was attempted.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT",
                      tempfile.mkdtemp(prefix="wh_pivot_"))

from valuation_ratios import ingest


@pytest.fixture()
def warehouse(monkeypatch, tmp_path):
    from institutional_warehouse import db

    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    monkeypatch.delenv("INSTITUTIONAL_WAREHOUSE_DATABASE_URL", raising=False)
    monkeypatch.delenv("WAREHOUSE_DATABASE_URL", raising=False)
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _seed(symbol, date, close=None):
    from institutional_warehouse import gateway

    gateway.write("valuation_ratios", [
        {"symbol": symbol, "isin": f"INE{symbol}", "ratio_name": name,
         "company_value": value, "sector_value": 18.0, "reported_date": date,
         "reported_time": f"{date}T12:00:00Z", "snapshot_id": f"s-{symbol}-{date}",
         "provider": "upstox"}
        for name, value in (("pe", 21.0), ("pb", 3.0), ("roe", 15.0))
    ], source="upstox", actor="t")
    if close is not None:
        gateway.write("daily_market_history",
                      [{"symbol": symbol, "date": date, "close": close}],
                      source="test", actor="t")


def _valuations():
    from institutional_warehouse import db

    return db.query(
        f"SELECT symbol, date, cmp, pe FROM {db.physical_table('historical_valuation')}")


def test_it_rebuilds_the_day_from_ratios_already_held(warehouse):
    _seed("AAA", "2026-08-23", close=101.5)
    assert _valuations() == []

    out = ingest.pivot_stored_ratios(date="2026-08-23", actor="t")

    assert out["ok"] and out["companies"] == 1 and out["ratio_rows"] == 3
    row = _valuations()[0]
    assert row["symbol"] == "AAA" and row["pe"] == 21.0 and row["cmp"] == 101.5


def test_it_spends_no_provider_budget(warehouse):
    """The point: the numbers are already held, re-fetching them is waste."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(ingest.pivot_stored_ratios).strip())
    fn = tree.body[0]
    # Drop the docstring: it describes the network the function avoids, and
    # matching prose is not a test of behaviour.
    body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                           and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    code = "\n".join(ast.dump(node) for node in body)
    for banned in ("urllib", "requests", "urlopen", "fetch_ratios"):
        assert banned not in code, f"pivot must not reach the provider: {banned}"


def test_only_the_requested_day_is_touched(warehouse):
    _seed("AAA", "2026-08-22", close=100.0)
    _seed("AAA", "2026-08-23", close=110.0)

    ingest.pivot_stored_ratios(date="2026-08-23", actor="t")

    dates = {r["date"] for r in _valuations()}
    assert dates == {"2026-08-23"}


def test_a_day_with_no_ratios_says_so(warehouse):
    out = ingest.pivot_stored_ratios(date="2026-01-01", actor="t")
    assert out["ok"] is False and out["error"] == "no_ratios_for_date"


def test_running_it_twice_does_not_duplicate(warehouse):
    """Repair has to be safe to re-run; the key is (symbol, date)."""
    _seed("AAA", "2026-08-23", close=101.5)
    ingest.pivot_stored_ratios(date="2026-08-23", actor="t")
    ingest.pivot_stored_ratios(date="2026-08-23", actor="t")

    assert len(_valuations()) == 1
