"""Nifty / NSE index constituent registry tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EXPECTED = {
    "NIFTY_50": 50,
    "NIFTY_NEXT_50": 50,
    "NIFTY_100": 100,
    "NIFTY_200": 200,
    "NIFTY_500": 500,
    "NIFTY_MIDCAP_SELECT": 25,
    "NIFTY_BANK": 14,
    "NIFTY_FINANCIAL_SERVICES": 20,
}


def test_index_csv_files_present():
    for name in (
        "Nifty50.csv",
        "NiftyNext50.csv",
        "Nifty100.csv",
        "Nifty200.csv",
        "Nifty500.csv",
        "NiftyMidcapSelect.csv",
        "NiftyBank.csv",
        "NiftyFinancialServices.csv",
    ):
        assert (REPO / "indices" / name).exists(), name


def test_market_indices_health_and_counts():
    from market_indices.loader import health, list_members, _cached_members

    _cached_members.cache_clear()
    h = health()
    assert h["ok"] is True
    assert h["available_count"] >= 8
    for iid, n in EXPECTED.items():
        members = list_members(iid)
        assert len(members) == n, (iid, len(members), n)


def test_bank_and_fin_contain_hdfc():
    from market_indices.loader import get_index, membership_for_symbol

    bank = get_index("nifty bank")
    assert bank and "HDFCBANK" in bank["symbols"]
    fin = get_index("NIFTY_FINANCIAL_SERVICES")
    assert fin and "HDFCBANK" in fin["symbols"]
    mem = membership_for_symbol("HDFCBANK")
    assert "NIFTY_BANK" in mem["indices"]
    assert "NIFTY_50" in mem["indices"]


def test_idbi_in_nifty500_not_bank():
    from market_indices.loader import get_index, membership_for_symbol

    n500 = get_index("NIFTY_500")
    assert n500 and "IDBI" in n500["symbols"]
    mem = membership_for_symbol("IDBI")
    assert "NIFTY_500" in mem["indices"]
    assert "NIFTY_BANK" not in mem["indices"]


def test_seed_universes_use_csv_members():
    from universe_intelligence.fixtures.seed_universes import universe_definitions

    defs = {u["universe_id"]: u for u in universe_definitions()}
    assert len(defs["NIFTY_BANK"]["members"]) == 14
    assert len(defs["NIFTY_200"]["members"]) == 200
    assert "HDFCBANK" in defs["NIFTY_BANK"]["members"]


def test_ask_soft_slice_answers_membership_and_constituents():
    from market_indices.production import soft_slice_for_ask_agi

    mem = soft_slice_for_ask_agi(
        "Which indices does HDFC Bank come under?",
        {"ticker": "HDFCBANK"},
    )["market_indices"]
    assert mem["answerable"] is True
    assert "Nifty Bank" in mem["direct_answer"]
    assert "Nifty 50" in mem["direct_answer"]

    cons = soft_slice_for_ask_agi("Which stocks are in Nifty Bank?")["market_indices"]
    assert cons["answerable"] is True
    assert cons["answer"]["count"] == 14
    assert "HDFCBANK" in cons["answer"]["symbols"]
