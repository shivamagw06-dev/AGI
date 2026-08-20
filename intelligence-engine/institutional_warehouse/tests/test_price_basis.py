"""Declaring what a stored price means, instead of reading it off a name."""

from __future__ import annotations

import pytest

from institutional_warehouse import price_basis as pb


class TestDescribe:
    def test_upstox_is_adjusted_under_either_writer_name(self):
        """The deep backfill and the nightly top-up are one feed. Split apart,
        one fails the freshness test and the other has no history."""
        assert pb.describe("upstox_v3_historical") == ("upstox", pb.SPLIT_ADJUSTED)
        assert pb.describe("upstox_v3_daily") == ("upstox", pb.SPLIT_ADJUSTED)

    def test_the_exchange_file_is_the_price_that_traded(self):
        assert pb.describe("nse_bhavcopy") == ("nse", pb.RAW)

    def test_yahoo_close_is_unadjusted(self):
        """The reader takes indicators.quote.close and keeps adjclose in its own
        column, so `close` is the raw price despite Yahoo offering both."""
        assert pb.describe("yahoo_finance_history")[1] == pb.RAW

    def test_an_unrecognised_source_is_unknown_not_assumed(self):
        """A wrong basis is worse than an absent one - it lets a reader pair two
        prices that do not belong together while believing it checked."""
        assert pb.describe("some_new_vendor")[1] == pb.UNKNOWN
        assert pb.describe(None)[1] == pb.UNKNOWN


class TestStamp:
    def test_a_price_row_carries_its_basis(self):
        [row] = pb.stamp([{"symbol": "X", "date": "2026-08-20", "close": 100.0}],
                         source="nse_bhavcopy")
        assert row["price_basis"] == pb.RAW
        assert row["feed_family"] == "nse"

    def test_a_row_with_no_price_is_left_alone(self):
        """The formula engine updates market_cap on rows it did not price.
        Stamping those relabels somebody else's number."""
        [row] = pb.stamp([{"symbol": "X", "date": "2026-08-20", "market_cap": 5.0}],
                         source="formula_engine")
        assert "price_basis" not in row

    def test_stamping_does_not_mutate_the_caller_s_rows(self):
        original = {"symbol": "X", "date": "2026-08-20", "close": 100.0}
        pb.stamp([original], source="nse_bhavcopy")
        assert "price_basis" not in original


class TestComparable:
    def test_two_prices_on_the_same_basis_may_be_divided(self):
        assert pb.comparable(pb.SPLIT_ADJUSTED, pb.SPLIT_ADJUSTED)
        assert pb.comparable(pb.RAW, pb.RAW)

    def test_a_raw_price_and_an_adjusted_one_may_not(self):
        """This is the Lal PathLabs defect in one line."""
        assert not pb.comparable(pb.RAW, pb.SPLIT_ADJUSTED)

    def test_two_unknowns_are_not_comparable_just_because_they_match(self):
        """Neither has been established, so their agreement means nothing."""
        assert not pb.comparable(pb.UNKNOWN, pb.UNKNOWN)

    @pytest.mark.parametrize("value", [None, "", "raw", "Split_Adjusted"])
    def test_case_and_blanks_are_handled(self, value):
        pb.comparable(value, pb.RAW)  # must not raise


class TestVendorPrefixes:
    """Writer names multiply; the vendor behind them does not.

    `upstox_v3_historical` is the backfill, `upstox_v3_daily` the nightly
    top-up, and `upstox_v3` a third that stamped 4,500 rows UNKNOWN before
    anyone noticed. Every Upstox v3 candle comes back restated for splits,
    whichever writer asked for it.
    """

    @pytest.mark.parametrize("source", ["upstox_v3", "upstox_v3_daily",
                                        "upstox_v3_historical", "upstox_v3_intraday"])
    def test_every_upstox_writer_resolves_to_the_same_feed(self, source):
        assert pb.describe(source) == ("upstox", pb.SPLIT_ADJUSTED)

    def test_a_vendor_we_have_not_declared_is_still_unknown(self):
        """This widens what is recognised; it does not guess."""
        assert pb.describe("zerodha_kite")[1] == pb.UNKNOWN
        assert pb.describe("formula_engine")[1] == pb.UNKNOWN

    def test_the_exchange_file_keeps_its_own_family(self):
        assert pb.describe("nse_bhavcopy_full") == ("nse", pb.RAW)
