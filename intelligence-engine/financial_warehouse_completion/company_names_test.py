"""A repair that writes the wrong name is worse than the ticker it replaced."""
from __future__ import annotations

import sys
import types

from financial_warehouse_completion import company_names


def _universe(monkeypatch, rows):
    monkeypatch.setitem(
        sys.modules, "trading_universe.loader",
        types.SimpleNamespace(load_rows=lambda: rows),
    )


def test_real_name_never_returns_the_ticker(monkeypatch):
    # The whole defect is `real_name(s) or s`. A source row that already
    # carries its ticker as its name must not be handed back as a real name.
    _universe(monkeypatch, [
        {"symbol": "HNDFDS", "name": "Hindustan Foods Limited"},
        {"symbol": "3PLAND", "name": "3PLAND"},          # ticker as name
        {"symbol": "HLVLTD", "name": " HLVLTD "},        # ticker, padded
    ])
    assert company_names.real_name("HNDFDS") == "Hindustan Foods Limited"
    assert company_names.real_name("3PLAND") is None
    assert company_names.real_name("HLVLTD") is None


def test_unknown_symbol_returns_none_not_the_symbol(monkeypatch):
    _universe(monkeypatch, [{"symbol": "HNDFDS", "name": "Hindustan Foods Limited"}])
    assert company_names.real_name("NOSUCH") is None


def test_a_name_that_looks_like_its_ticker_is_left_alone(monkeypatch):
    # "BLB Limited" normalises to blblimited, which equals the symbol BLB
    # LIMITED. That is a correct name, not damage, and rewriting it would be
    # churn dressed up as a fix.
    _universe(monkeypatch, [{"symbol": "BLBLIMITED", "name": "BLB Limited"}])
    assert company_names.real_name("BLBLIMITED") is None


def test_audit_separates_repairable_from_hopeless(monkeypatch):
    _universe(monkeypatch, [
        {"symbol": "HNDFDS", "name": "Hindustan Foods Limited"},
    ])
    monkeypatch.setitem(sys.modules, "institutional_warehouse.store",
        types.SimpleNamespace(all_rows=lambda tab, limit=0: [
            {"symbol": "HNDFDS", "company_name": "HNDFDS"},        # fixable
            {"symbol": "ABSLPSE", "company_name": "ABSLPSE"},      # no name anywhere
            {"symbol": "TCS", "company_name": "Tata Consultancy"}, # already fine
        ]))
    out = company_names.audit()
    assert out["ok"] is True
    assert out["repairable"] == 1
    assert out["no_name_available"] == 1
    assert out["named"] == 1


def test_repair_defaults_to_dry_run(monkeypatch):
    # A data repair that runs on import, or on a GET, is how 2,714 rows get
    # rewritten by accident.
    _universe(monkeypatch, [{"symbol": "HNDFDS", "name": "Hindustan Foods Limited"}])
    monkeypatch.setitem(sys.modules, "institutional_warehouse.store",
        types.SimpleNamespace(all_rows=lambda tab, limit=0: [
            {"symbol": "HNDFDS", "company_name": "HNDFDS"}]))
    wrote = []
    monkeypatch.setitem(sys.modules, "institutional_warehouse.gateway",
        types.SimpleNamespace(write=lambda *a, **k: wrote.append(a) or {"written": 1}))
    out = company_names.repair()
    assert out["dry_run"] is True
    assert out["would_write"] == 1
    assert out["written"] == 0
    assert wrote == [], "dry run must not write"


def test_repair_only_touches_rows_named_after_their_ticker(monkeypatch):
    # A row with a real name is left alone even where the universe file
    # disagrees. This repairs a known defect; it does not arbitrate names.
    _universe(monkeypatch, [
        {"symbol": "HNDFDS", "name": "Hindustan Foods Limited"},
        {"symbol": "TCS", "name": "Tata Consultancy Services Limited"},
    ])
    monkeypatch.setitem(sys.modules, "institutional_warehouse.store",
        types.SimpleNamespace(all_rows=lambda tab, limit=0: [
            {"symbol": "HNDFDS", "company_name": "HNDFDS"},
            {"symbol": "TCS", "company_name": "Tata Consultancy"},
        ]))
    sent = {}
    monkeypatch.setitem(sys.modules, "institutional_warehouse.gateway",
        types.SimpleNamespace(write=lambda tab, rows, **k: sent.update(rows=rows)
                              or {"written": len(rows), "updated": len(rows)}))
    out = company_names.repair(dry_run=False)
    assert out["written"] == 1
    assert [r["symbol"] for r in sent["rows"]] == ["HNDFDS"]
