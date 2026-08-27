"""IKT onboarding — every company in the uploaded universe file gets a
company_master row automatically, with no code changes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", "/tmp/ikt_sync_test_store")

from institutional_knowledge_tables.store import delete_company, get_table


def setup_function():
    for t in ("HDFCBANK", "IDBI", "RELIANCE"):
        delete_company(t)


def test_sync_company_master_writes_only_real_fields():
    from institutional_knowledge_tables.sync import sync_company_master

    out = sync_company_master("HDFCBANK")
    assert out["ok"] is True
    assert "company_name" in out["fields_written"]
    assert "ticker" in out["fields_written"]

    table = get_table("HDFCBANK", "company_master")
    assert table["row"]["ticker"]["value"] == "HDFCBANK"
    assert table["row"]["ticker"]["source"] == "trading_universe+market_indices"
    # Fields with no real source data must remain unpopulated, not guessed.
    assert table["row"]["cin"] is None
    assert table["row"]["website"] is None


def test_sync_unknown_ticker_fails_cleanly():
    from institutional_knowledge_tables.sync import sync_company_master

    out = sync_company_master("NOTASYMBOLXYZ")
    assert out["ok"] is False
    assert out["error"] == "not_in_trading_universe"


def test_onboard_universe_bounded_scope():
    from institutional_knowledge_tables.sync import sync_universe_company_master

    out = sync_universe_company_master(scope="nifty500", limit=10)
    assert out["ok"] is True
    assert out["attempted"] == 10
    assert out["synced"] == 10
    assert out["failed"] == 0
