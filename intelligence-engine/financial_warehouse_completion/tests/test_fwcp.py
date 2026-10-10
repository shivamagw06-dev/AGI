"""FWCP unit tests — no live vendors."""

from __future__ import annotations

from financial_warehouse_completion.dqiv_rules import (
    reject_vendor_multiples,
    validate_share_count_row,
    validate_statement_row,
)
from financial_warehouse_completion.models import PROGRAMME_CODE, TARGETS
from financial_warehouse_completion.production import health, import_board, import_status


def test_health_surface():
    h = health()
    assert h["ok"] is True
    assert h["programme"] == PROGRAMME_CODE
    assert h["vendor_historical_multiples"] is False
    assert h["creates_intelligence"] is False
    assert "financial-coverage" in " ".join(h["endpoints"])


def test_targets_defined():
    assert TARGETS["annual_pct"] >= 95
    assert TARGETS["share_count_pct"] >= 99
    assert TARGETS["hvie_complete_pct"] >= 90


def test_share_count_dqiv_rejects_non_positive():
    bad = validate_share_count_row({"shares_outstanding": -1})
    assert bad["ok"] is False
    good = validate_share_count_row({"shares_outstanding": 1_000_000, "diluted_shares": 1_050_000})
    assert good["ok"] is True
    assert good["canonical_shares"] == 1_000_000


def test_statement_dqiv_balance_sheet():
    ok = validate_statement_row(
        {
            "fiscal_year": "FY24",
            "total_assets": 100,
            "total_liabilities": 40,
            "total_equity": 60,
            "shares_outstanding": 10,
            "currency": "INR",
        }
    )
    assert ok["ok"] is True
    fail = validate_statement_row(
        {
            "fiscal_year": "FY24",
            "total_assets": 100,
            "total_liabilities": 10,
            "total_equity": 10,
            "shares_outstanding": 10,
        }
    )
    assert fail["ok"] is False


def test_reject_vendor_multiples():
    hits = reject_vendor_multiples({"pe": 22.5, "source": "capital_iq"})
    assert "pe" in hits
    assert reject_vendor_multiples({"pe": 22.5, "source": "warehouse_reconstruction"}) == []


def test_import_status_idle():
    st = import_status()
    assert st["ok"] is True
    assert st["runtime"]["status"] in {"idle", "running", "stopped"}
    board = import_board()
    assert board["ok"] is True
    assert "share_count_history" in board["packs"]
