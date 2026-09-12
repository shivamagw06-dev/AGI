"""Universe Master Registry — single source of truth from uploaded universe files."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", "/tmp/umr_test_store")


def test_registry_sourced_from_real_universe_files():
    from universe_master_registry.registry import build_company_row, dashboard

    row = build_company_row("HDFCBANK")
    assert row is not None
    assert row["ticker"] == "HDFCBANK"
    assert row["exchange"] == "NSE"
    assert "NIFTY_50" in row["index_membership"]
    assert "NIFTY_BANK" in row["index_membership"]

    idbi = build_company_row("IDBI")
    assert idbi is not None
    assert "NIFTY_500" in idbi["index_membership"]
    assert "NIFTY_BANK" not in idbi["index_membership"]

    d = dashboard()
    assert d["trading_universe_count"] >= 2300
    assert d["index_summary"]["nifty_500"] == 500


def test_unknown_ticker_not_fabricated():
    from universe_master_registry.registry import build_company_row, get_company

    assert build_company_row("NOTASYMBOLXYZ") is None
    result = get_company("NOTASYMBOLXYZ")
    assert result["ok"] is False
    assert result["error"] == "not_in_universe_master_registry"


def test_get_company_never_fabricates_coverage_when_unreachable():
    from universe_master_registry.registry import get_company

    result = get_company("HDFCBANK")
    assert result["ok"] is True
    # institutional_coverage_factory may or may not be reachable in this test
    # environment; either way the field must be a real signal or explicitly None —
    # never a guessed True/False.
    assert result["institutional_coverage"] in (True, False, None)
    if result.get("signal_source") is None:
        assert result["institutional_coverage"] is None
        assert result["knowledge_confidence"] is None


def test_list_registry_index_filter():
    from universe_master_registry.registry import list_registry

    out = list_registry(index="NIFTY_BANK")
    assert out["ok"] is True
    assert out["count"] == 14
    tickers = {r["ticker"] for r in out["rows"]}
    assert "HDFCBANK" in tickers
    assert "IDBI" not in tickers
