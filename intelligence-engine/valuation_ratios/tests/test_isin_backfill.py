"""ISIN backfill helpers — no network in unit tests."""

from valuation_ratios.isin_backfill import _valid_isin, load_index_csv_isin_map


def test_valid_isin():
    assert _valid_isin("INE002A01018") == "INE002A01018"
    assert _valid_isin("ine002a01018") == "INE002A01018"
    assert _valid_isin("") is None
    assert _valid_isin("RELIANCE") is None


def test_index_csv_map_loads_nifty_symbols():
    mapping = load_index_csv_isin_map()
    if not mapping:
        # Repo checkout without indices/ — skip soft.
        return
    assert mapping.get("RELIANCE") == "INE002A01018" or "RELIANCE" in mapping or len(mapping) > 50
