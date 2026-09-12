"""Bulk company-info sheet ingest — Excel/CSV → versioned IKT facts."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", "/tmp/ikt_bulk_sheet_test_store")

import pandas as pd

from institutional_knowledge_tables.bulk_sheet import ingest_company_sheet
from institutional_knowledge_tables.store import delete_company, get_field_history, get_table


def _xlsx_bytes(df: "pd.DataFrame") -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def setup_function():
    for t in ("HDFCBANK", "IDBI", "RELIANCE", "ABB", "BSE500191", "HMT", "BSEPRESSMN", "AAKAAR", "TOTALLYFAKEXYZ"):
        delete_company(t)


def test_ingest_by_exact_ticker():
    df = pd.DataFrame(
        [
            {"Ticker": "HDFCBANK", "Sector": "Banking", "CEO": "Sashidhar Jagdishan", "PE": 18.4},
            {"Ticker": "IDBI", "Sector": "Banking", "CEO": "Rakesh Sharma", "PE": 12.1},
        ]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "companies.xlsx")
    assert out["ok"] is True
    assert out["resolved_count"] == 2
    assert out["unresolved_count"] == 0
    assert "company_master.sector" in out["mapped_columns"].values()
    assert "management.ceo" in out["mapped_columns"].values()
    assert "valuation.pe" in out["mapped_columns"].values()

    sector_hist = get_field_history("HDFCBANK", "company_master", "sector")
    assert sector_hist[-1]["value"] == "Banking"
    assert sector_hist[-1]["source"].startswith("bulk_upload:companies.xlsx")

    ceo = get_table("IDBI", "management")
    assert ceo["row"]["ceo"]["value"] == "Rakesh Sharma"


def test_ingest_by_company_name_when_no_ticker():
    df = pd.DataFrame([{"Company Name": "IDBI Bank Limited", "Industry": "Bank"}])
    out = ingest_company_sheet(_xlsx_bytes(df), "names_only.xlsx")
    assert out["ok"] is True
    assert out["resolved_count"] == 1
    assert out["resolved_sample"][0]["ticker"] == "IDBI"
    assert out["resolved_sample"][0]["method"] == "exact_name_match"


def test_unresolved_rows_are_reported_not_guessed():
    df = pd.DataFrame(
        [
            {"Ticker": "HDFCBANK", "Sector": "Banking"},
            {"Ticker": "TOTALLYFAKEXYZ", "Sector": "Nowhere"},
        ]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "mixed.xlsx")
    assert out["resolved_count"] == 1
    assert out["unresolved_count"] == 1
    assert out["unresolved_rows"][0]["ticker_raw"] == "TOTALLYFAKEXYZ"
    assert out["unresolved_rows"][0]["reason"] == "unresolved"
    # never fabricated a table row for the unresolved ticker
    from institutional_knowledge_tables.store import get_table as _gt

    fake = _gt("TOTALLYFAKEXYZ", "company_master")
    assert fake["missing_fields"] == list(fake["row"].keys())


def test_dry_run_does_not_write():
    df = pd.DataFrame([{"Ticker": "RELIANCE", "Sector": "Energy"}])
    out = ingest_company_sheet(_xlsx_bytes(df), "dry.xlsx", dry_run=True)
    assert out["ok"] is True
    assert out["resolved_count"] == 1
    table = get_table("RELIANCE", "company_master")
    assert table["row"]["sector"] is None  # nothing actually written


def test_unmapped_columns_reported():
    df = pd.DataFrame([{"Ticker": "RELIANCE", "Some Random Column": "xyz"}])
    out = ingest_company_sheet(_xlsx_bytes(df), "extra.xlsx")
    assert "Some Random Column" in out["unmapped_columns"]


def test_missing_ticker_and_name_column_rejected():
    df = pd.DataFrame([{"Sector": "Energy"}])
    out = ingest_company_sheet(_xlsx_bytes(df), "no_id.xlsx")
    assert out["ok"] is False
    assert out["error"] == "no_ticker_or_company_name_column"


def test_csv_input_also_supported():
    csv_bytes = b"Ticker,Sector\nHDFCBANK,Banking\n"
    out = ingest_company_sheet(csv_bytes, "companies.csv")
    assert out["ok"] is True
    assert out["resolved_count"] == 1


def test_exchange_prefixed_ticker_resolves_and_writes_canonical_value():
    """A raw sheet code like 'BSE:500180' must resolve via company name and
    the written company_master.ticker fact must be the canonical ticker,
    never the raw exchange-prefixed source code."""
    df = pd.DataFrame(
        [{"Ticker": "BSE:500180", "Company Name": "HDFC Bank Limited", "Primary Sector": "Financials"}]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "capiq_style.xlsx")
    assert out["ok"] is True
    assert out["resolved_count"] == 1
    assert out["resolved_sample"][0]["ticker"] == "HDFCBANK"

    table = get_table("HDFCBANK", "company_master")
    assert table["row"]["ticker"]["value"] == "HDFCBANK"
    assert table["row"]["sector"]["value"] == "Financials"


def test_headerless_continuation_file_reuses_column_names():
    """A second export batch from the same saved screen often has no header
    row — reuse the header list from the first file positionally."""
    headers = ["Ticker", "Company Name", "Primary Sector"]
    # Data-only rows, no header
    df = pd.DataFrame([["RELIANCE", "Reliance Industries Limited", "Energy"]])
    out = ingest_company_sheet(
        _xlsx_bytes(df), "continuation.xlsx", column_names=headers
    )
    assert out["ok"] is True
    assert out["resolved_count"] == 1
    assert out["mapped_columns"]["Primary Sector"] == "company_master.sector"


def test_headerless_column_count_mismatch_reported():
    headers = ["Ticker", "Company Name", "Primary Sector", "Extra Column"]
    df = pd.DataFrame([["RELIANCE", "Reliance Industries Limited", "Energy"]])
    out = ingest_company_sheet(_xlsx_bytes(df), "bad.xlsx", column_names=headers)
    assert out["ok"] is False
    assert "column_count_mismatch" in out["error"]


def test_ltm_and_latest_period_labels_inferred_from_header():
    df = pd.DataFrame(
        [
            {
                "Ticker": "RELIANCE",
                "EBITDA [LTM] ($USDmm, Historical rate)": 12000,
                "Market Capitalization [My Setting] [Latest] ($USDmm, Historical rate)": 250000,
            }
        ]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "capiq2.xlsx")
    assert out["ok"] is True
    fin = get_table("RELIANCE", "financial_statements", period="LTM")
    assert fin["found"] is True
    assert fin["row"]["ebitda"]["value"] == 12000
    market = get_table("RELIANCE", "market_data", period="latest")
    assert market["found"] is True
    assert market["row"]["market_cap"]["value"] == 250000


def test_dash_placeholder_values_are_treated_as_blank_not_stored():
    """Capital IQ / screener exports use a bare '-' for 'no data available'
    — this must never be written as if it were a real fact value (found
    via live 460/2035.xlsx ingestion: Business Description='-' was
    overwriting a real, populated description_short elsewhere)."""

    df = pd.DataFrame(
        [
            {
                "Ticker": "RELIANCE",
                "Long Business Description": "-",
                "Website": "-",
                "Native Language Company Name": "-",
                "Primary Sector": "Energy",
            }
        ]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "dashes.xlsx")
    assert out["ok"] is True
    biz = get_table("RELIANCE", "business_model")
    assert biz["row"]["description"] is None
    master = get_table("RELIANCE", "company_master")
    assert master["row"]["website"] is None
    assert master["row"]["native_name"] is None
    assert master["row"]["sector"]["value"] == "Energy"  # real value still written


def test_capital_iq_full_column_set_all_mapped_no_unmapped():
    """All 40 columns of the actual 460.xlsx/2035.xlsx export shape must be
    recognized — regression guard for the Phase 2.6+ bulk-upload extension
    that added returns_*, currency, company_type, native_name,
    parent_company, external_id, research_coverage_count, investors,
    industry_classifications, subsidiaries_count, description_short,
    index_constituents, next_earnings_date_* and product_description."""

    df = pd.DataFrame(
        [
            {
                "Ticker": "BSE:500002",
                "Company Name": "ABB India Limited",
                "Index Constituents (All Equity Listings)": "S&P Global Ex-Japan LargeCap Growth",
                "Trading Status": "Active",
                "Excel Trading Item ID": "IQT34636426",
                "Equity Currency": "Indian Rupee",
                "Day Close Price [Latest] ($USD, Historical rate)": 76.3,
                "% Price Change [YTD as of 1/1/2026]": 41.3,
                "% Price Change [1 Day]": 0.926,
                "% Price Change [1 Week]": -2.59,
                "% Price Change [1 Month]": 2.55,
                "% Price Change [3 Months]": 0.661,
                "% Price Change [6 Months]": 33.5,
                "% Price Change [9 Months]": 38.2,
                "% Price Change [1 Year]": 31.0,
                "% Price Change [3 Years]": 61.9,
                "% Price Change [5 Years]": 334.3,
                "Daily Volume (Average - 3 Months) [Latest]": 0.019,
                "Primary Sector": "Industrials",
                "Primary Industry": "Heavy Electrical Equipment",
                "Industry Classifications": "Industrials (Primary)",
                "Current and Pending Investors": "ABB Asea Brown Boveri Ltd (Current Parent)",
                "Ultimate Corporate Parent": "ABB Ltd (SWX:ABBN)",
                "Exchange Country/Region": "India",
                "Business Description": "ABB India Limited develops and sells products.",
                "# of Total Investments / Subsidiaries": 13,
                "Company Type": "Public Company",
                "Competitors": "Siemens Limited; Larsen & Toubro Limited",
                "EBITDA [LTM] ($USDmm, Historical rate)": 200.2,
                "Total Enterprise Value [My Setting] [Latest] ($USDmm, Historical rate)": 15584.7,
                "Total Revenue [LTM] ($USDmm, Historical rate)": 1426.6,
                "Market Capitalization [My Setting] [Latest] ($USDmm, Historical rate)": 16186.2,
                "Long Business Description": "ABB India Limited (ABB) is an engineering company.",
                "Native Language Company Name": "-",
                "Next Announced Earnings Date": "2026-07-31",
                "Next Expected Earnings Date": "2026-07-31",
                "Number of Investment Research Documents [Last 30 Days]": 13,
                "Product Description": "ABB Ability SmartMaster: asset performance management.",
                "Product Name": "ABB Ability SmartMaster; AFS Contactors",
                "Website": "new.abb.com/indian-subcontinent",
            }
        ]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "full_capiq_export.xlsx")
    assert out["ok"] is True
    assert out["unmapped_columns"] == []
    assert out["resolved_count"] == 1

    master = get_table("ABB", "company_master")
    assert master["row"]["currency"]["value"] == "Indian Rupee"
    assert master["row"]["company_type"]["value"] == "Public Company"
    assert master["row"]["parent_company"]["value"] == "ABB Ltd (SWX:ABBN)"
    assert master["row"]["external_id"]["value"] == "IQT34636426"
    assert master["row"]["research_coverage_count"]["value"] == 13
    assert master["row"]["native_name"] is None  # "-" placeholder skipped

    biz = get_table("ABB", "business_model")
    assert biz["row"]["description_short"]["value"].startswith("ABB India Limited develops")
    assert biz["row"]["industry_classifications"]["value"] == "Industrials (Primary)"
    assert biz["row"]["investors"]["value"].startswith("ABB Asea Brown Boveri")
    assert biz["row"]["subsidiaries_count"]["value"] == 13
    assert biz["row"]["index_constituents"]["value"].startswith("S&P Global")

    products = get_table("ABB", "products")
    assert products["row"]["product_description"]["value"].startswith("ABB Ability SmartMaster")

    market = get_table("ABB", "market_data", period="latest")
    assert market["found"] is True
    row = market["row"]
    assert row["returns_1d"]["value"] == 0.926
    assert row["returns_1w"]["value"] == -2.59
    assert row["returns_3m"]["value"] == 0.661
    assert row["returns_6m"]["value"] == 33.5
    assert row["returns_9m"]["value"] == 38.2
    assert row["returns_3y"]["value"] == 61.9
    assert row["returns_5y"]["value"] == 334.3
    assert row["returns_ytd"]["value"] == 41.3
    assert row["next_earnings_date_announced"]["value"] == "2026-07-31"
    assert row["next_earnings_date_expected"]["value"] == "2026-07-31"


def test_bse_only_company_resolves_via_bse_code_fallback():
    """A company with no NSE listing (common for smaller/legacy BSE-only
    names) must still resolve using its own real BSE code from the sheet,
    rather than being dropped as unresolved."""

    df = pd.DataFrame(
        [{"Ticker": "BSE:500191", "Company Name": "HMT Limited", "Primary Sector": "Industrials"}]
    )
    out = ingest_company_sheet(_xlsx_bytes(df), "bse_only.xlsx")
    assert out["ok"] is True
    assert out["resolved_count"] == 1
    assert out["resolved_sample"][0]["ticker"] == "BSE500191"
    assert out["resolved_sample"][0]["method"] == "bse_code_fallback"

    master = get_table("BSE500191", "company_master")
    assert master["row"]["ticker"]["value"] == "BSE500191"
    assert master["row"]["sector"]["value"] == "Industrials"


def test_bse_code_fallback_not_used_when_no_bse_prefix_present():
    """A genuinely fabricated/unrecognized name+ticker combination must
    still be reported unresolved — the BSE fallback only accepts an
    explicit, well-formed 'BSE:NNNNNN' code, never invents one."""

    df = pd.DataFrame([{"Ticker": "TOTALLYFAKEXYZ", "Company Name": "Not A Real Company Ltd"}])
    out = ingest_company_sheet(_xlsx_bytes(df), "fake.xlsx")
    assert out["resolved_count"] == 0
    assert out["unresolved_count"] == 1
    assert out["unresolved_rows"][0]["reason"] == "unresolved"


def test_generic_middle_word_company_does_not_collide_with_unrelated_ticker():
    """Regression: 'Titan Company Limited' must resolve to TITAN, and a
    totally unrelated 'Titan Biotech Limited' row must never be silently
    bound to that same ticker. 'Company' is a genuine, distinguishing word
    in many Indian legal names (Titan Company Ltd, Tata Power Company Ltd)
    — stripping it as a generic suffix collapsed 'Titan Company Limited'
    down to just 'titan', which then wrongly fuzzy-matched any other
    'Titan *' company."""
    from institutional_knowledge_tables.bulk_sheet import resolve_ticker

    ticker, method = resolve_ticker(None, "Titan Company Limited")
    assert ticker == "TITAN"
    assert method == "exact_name_match"

    ticker2, method2 = resolve_ticker("BSE:507590", "Titan Biotech Limited")
    assert ticker2 != "TITAN"
    assert ticker2 == "BSE507590"
    assert method2 == "bse_code_fallback"


def test_short_ticker_word_does_not_match_as_raw_substring_of_unrelated_name():
    """Regression: a 3-letter listed name like 'ACC Limited' (-> 'acc') must
    never match purely because those letters occur inside an unrelated
    word, e.g. 'tobacco' contains the substring 'acc'. Matching must be
    word-boundary based, not raw character containment."""
    from institutional_knowledge_tables.bulk_sheet import resolve_ticker

    ticker, method = resolve_ticker(None, "ACC Limited")
    assert ticker == "ACC"
    assert method == "exact_name_match"

    ticker2, method2 = resolve_ticker("BSE:507815", "Golden Tobacco Limited")
    assert ticker2 != "ACC"
    assert ticker2 == "BSE507815"
    assert method2 == "bse_code_fallback"


def test_nsei_prefixed_sme_ticker_falls_back_to_bare_nse_symbol():
    """CapIQ marks many SME/small-cap NSE listings as 'NSEI:<SYMBOL>' that
    are not in the (Nifty-anchored) trading_universe. The source-supplied
    symbol itself must become the canonical ticker — never dropped, never
    invented under a different key."""
    from institutional_knowledge_tables.bulk_sheet import resolve_ticker

    ticker, method = resolve_ticker("NSEI:AAKAAR", "Aakaar Medical Technologies Ltd.")
    assert ticker == "AAKAAR"
    assert method == "nse_ticker_fallback"

    # 'NSE:' (without the trailing I) must also strip and fall back the same way
    # when the symbol isn't in the universe.
    ticker2, method2 = resolve_ticker("NSE:3RDROCK", "3rd Rock Multimedia Limited")
    assert ticker2 == "3RDROCK"
    assert method2 == "nse_ticker_fallback"


def test_bse_alphabetic_symbol_falls_back_like_numeric_code():
    """A few CapIQ BSE rows carry an alphabetic symbol ('BSE:PRESSMN')
    rather than a 6-digit code. Same contract as the numeric fallback:
    use the source-supplied identifier, prefixed with BSE, never invent."""
    from institutional_knowledge_tables.bulk_sheet import resolve_ticker

    ticker, method = resolve_ticker("BSE:PRESSMN", "Pressman Advertising Limited")
    assert ticker == "BSEPRESSMN"
    assert method == "bse_code_fallback"


def test_name_canonical_dedup_prefers_nse_over_bse_key():
    """The same legal company can appear as BSE:500191 in one CapIQ chunk
    and NSEI:HMT in a later chunk. Facts must collapse onto one IKT key,
    preferring the bare NSE symbol, and the orphan BSE key must be removed
    so the company_router can't keep answering under the old identifier."""
    from institutional_knowledge_tables.bulk_sheet import ingest_company_sheet
    from institutional_knowledge_tables.store import get_table, list_companies

    name_canonical: dict = {}
    df_bse = pd.DataFrame(
        [{"Ticker": "BSE:500191", "Company Name": "HMT Limited", "Primary Sector": "Industrials"}]
    )
    out1 = ingest_company_sheet(_xlsx_bytes(df_bse), "bse_chunk.xlsx", name_canonical=name_canonical)
    assert out1["resolved_count"] == 1
    assert out1["resolved_sample"][0]["ticker"] == "BSE500191"

    df_nse = pd.DataFrame(
        [{"Ticker": "NSEI:HMT", "Company Name": "HMT Limited", "Primary Sector": "Industrials"}]
    )
    out2 = ingest_company_sheet(_xlsx_bytes(df_nse), "nse_chunk.xlsx", name_canonical=name_canonical)
    assert out2["resolved_count"] == 1
    assert out2["resolved_sample"][0]["ticker"] == "HMT"
    assert out2["superseded_count"] == 1

    assert "HMT" in list_companies()
    assert "BSE500191" not in list_companies()
    master = get_table("HMT", "company_master")
    assert master["row"]["company_name"]["value"] == "HMT Limited"
    assert master["row"]["ticker"]["value"] == "HMT"
    delete_company("HMT")


def test_fuzzy_word_subset_fallback_removed_no_wrong_company_binding():
    """Regression: names that are a superset/subset of another real,
    differently-ticker'd company's words (e.g. 'Reliance Infrastructure
    Limited' vs the distinct 'Reliance Industrial Infrastructure Limited'
    (RIIL); 'Shree Digvijay Cement Company Limited' vs the distinct 'Shree
    Cement Limited' (SHREECEM)) must never be guessed via fuzzy matching.
    Only an exact ticker, exact normalized name, or explicit BSE code may
    resolve a row."""
    from institutional_knowledge_tables.bulk_sheet import resolve_ticker

    riil, riil_method = resolve_ticker(None, "Reliance Industrial Infrastructure Limited")
    assert riil == "RIIL"
    assert riil_method == "exact_name_match"

    reliance_infra, method = resolve_ticker("BSE:500390", "Reliance Infrastructure Limited")
    assert reliance_infra != "RIIL"
    assert reliance_infra == "BSE500390"
    assert method == "bse_code_fallback"

    shreecem, shreecem_method = resolve_ticker(None, "Shree Cement Limited")
    assert shreecem == "SHREECEM"
    assert shreecem_method == "exact_name_match"

    digvijay, digvijay_method = resolve_ticker("BSE:502180", "Shree Digvijay Cement Company Limited")
    assert digvijay != "SHREECEM"
    assert digvijay == "BSE502180"
    assert digvijay_method == "bse_code_fallback"
