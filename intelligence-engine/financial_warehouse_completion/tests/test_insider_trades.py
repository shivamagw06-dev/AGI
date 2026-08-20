"""Loading Trendlyne insider exports, and the traps in them.

The page these feed renders empty today: its live source answers HTTP 429 with
zero rows. These files carry the same disclosures at no per-request cost, but
three things about them will corrupt the result if handled naively - a 1,000
row download cap that silently truncates, heavy overlap between exports, and a
"mode" column that separates a real market purchase from a gift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from financial_warehouse_completion import insider_trades as it

HEADER = ('"Stock","Client Name","Client Category","Action*",'
          '"Reported To/By Exchange","Quantity","Post Transaction Holding",'
          '"Traded %","Avg. Price","Value","Period",'
          '"Regulation (Insider/SAST)","Security Type","Mode"')


def _csv(tmp_path: Path, name: str, *lines: str) -> Path:
    path = tmp_path / name
    path.write_text("\n".join([HEADER, *lines]), encoding="utf-8")
    return path


def _line(stock="Liberty Shoes", person="Anupam Bansal", category="Promoter",
          action="Acquisition", when="2026-08-20", qty="4548", post="665605",
          pct="0.03", price="244", value="1,109,712", mode="Market Purchase"):
    return (f'"{stock}","{person}","{category}","{action}","{when}","{qty}",'
            f'"{post}","{pct}","{price}","{value}","19 Aug 2026",'
            f'"Insider Trading","Equity","{mode}"')


class TestParsing:
    def test_reads_a_row(self, tmp_path):
        rows = it.parse_file(_csv(tmp_path, "insider_a.csv", _line()))
        assert len(rows) == 1
        row = rows[0]
        assert row["company_name"] == "Liberty Shoes"
        assert row["person"] == "Anupam Bansal"
        assert row["quantity"] == 4548
        assert row["value"] == 1109712, "thousands separators must not truncate the value"
        assert row["traded_pct"] == 0.03

    def test_a_dash_means_absent_not_zero(self, tmp_path):
        rows = it.parse_file(_csv(tmp_path, "insider_b.csv", _line(value="-", pct="-")))
        assert rows[0]["value"] is None
        assert rows[0]["traded_pct"] is None

    def test_rows_missing_a_key_part_are_skipped(self, tmp_path):
        """Storing these would silently merge unrelated filings together."""
        rows = it.parse_file(_csv(
            tmp_path, "insider_c.csv",
            _line(person=""), _line(qty=""), _line(when=""), _line(mode="")))
        assert rows == []


class TestOpenMarket:
    @pytest.mark.parametrize("mode,expected", [
        ("Market Purchase", "true"),
        ("Market Sale", "true"),
        ("Open Market", "true"),
        # These move shares without anyone paying a market price, so they are
        # not evidence of conviction.
        ("Gift", "false"),
        ("Off Market", "false"),
        ("Others", "false"),
    ])
    def test_only_real_market_trades_are_flagged(self, tmp_path, mode, expected):
        rows = it.parse_file(_csv(tmp_path, f"insider_{mode[:4]}.csv", _line(mode=mode)))
        assert rows[0]["is_open_market"] == expected


class TestOverlap:
    def test_the_same_trade_in_two_files_is_stored_once(self, tmp_path):
        """A six-month request returned 1,000 rows of which 912 already existed
        in the August files."""
        _csv(tmp_path, "insider_aug.csv", _line())
        _csv(tmp_path, "insider_range.csv", _line())
        out = it.parse(tmp_path)
        assert out["row_count"] == 1
        assert sum(f["duplicate"] for f in out["files"]) == 1

    def test_two_trades_by_one_person_on_one_day_are_both_kept(self, tmp_path):
        """A promoter can file twice in a session. Keying on person and date
        alone would collapse them into one."""
        _csv(tmp_path, "insider_two.csv",
             _line(qty="4548"), _line(qty="9000"))
        assert it.parse(tmp_path)["row_count"] == 2

    def test_a_buy_and_a_sell_are_not_merged(self, tmp_path):
        _csv(tmp_path, "insider_both.csv",
             _line(action="Acquisition"), _line(action="Disposal"))
        assert it.parse(tmp_path)["row_count"] == 2

    def test_no_files_fails_closed(self, tmp_path):
        assert it.parse(tmp_path)["error"] == "no_insider_exports_found"


class TestRealExports:
    def test_the_checked_in_files_load(self):
        out = it.parse()
        if not out.get("ok"):
            return  # exports absent in this checkout
        assert out["row_count"] > 900
        assert out["companies"] > 300

    def test_the_download_cap_is_declared(self):
        """A wide date range returns the newest 1,000 rows and looks complete."""
        out = it.parse()
        assert any("1,000 rows" in x for x in out.get("limitations", []))

    def test_partial_ticker_coverage_is_stated(self):
        """The export covers companies our master does not, so most rows keep a
        blank symbol rather than a fabricated one."""
        out = it.parse()
        assert any("third resolve" in x for x in out.get("limitations", []))


class TestSymbolResolution:
    INDEX = ({"shaily engineering plastics": "SHAILY",
              "apollo hospitals enterprise": "APOLLOHOSP",
              "reliance industries": "RELIANCE"},
             [("shaily engineering plastics", "SHAILY"),
              ("apollo hospitals enterprise", "APOLLOHOSP"),
              ("reliance industries", "RELIANCE"),
              ("reliance power", "RPOWER")])

    def test_an_exact_name_resolves(self):
        assert it.resolve_symbol("Reliance Industries Ltd", self.INDEX) == ("RELIANCE", "exact")

    def test_a_short_trade_name_resolves_by_prefix(self):
        """The export writes "Shaily Engineering" for "Shaily Engineering
        Plastics Limited"."""
        assert it.resolve_symbol("Shaily Engineering", self.INDEX) == ("SHAILY", "prefix")

    def test_an_ambiguous_prefix_resolves_to_nothing(self):
        """Two Reliance companies share the opening word. Attaching the trade to
        whichever sorts first would file it against the wrong company."""
        assert it.resolve_symbol("Reliance", self.INDEX) == (None, "ambiguous")

    def test_an_unknown_company_keeps_a_blank_symbol(self):
        assert it.resolve_symbol("Some Tiny Co", self.INDEX) == (None, "unmatched")

    def test_suffixes_and_punctuation_do_not_block_a_match(self):
        assert it.resolve_symbol("APOLLO HOSPITALS ENTERPRISE LIMITED.",
                                 self.INDEX)[0] == "APOLLOHOSP"
