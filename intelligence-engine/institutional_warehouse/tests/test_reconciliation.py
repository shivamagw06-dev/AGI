"""Reconciliation against an external reference.

Each test below is a defect that actually shipped on 2026-08-20 and was found
by a person comparing the page to a public quote, not by any automated check.
They are written as the numbers that were really on screen, so a regression
reads as the original incident rather than as an abstract threshold.
"""

from __future__ import annotations

import pytest

from institutional_warehouse import reconciliation as rc


class TestFieldComparison:
    def test_the_year_stale_return_would_have_failed(self):
        """The desk showed SUNTECK at +23.1% while the stock was down 25.1%."""
        out = rc.compare_field("return_1y", 23.1, -25.13)
        assert out["status"] == "FAIL"
        assert out["delta"] == pytest.approx(48.23, abs=0.01)

    def test_the_corrected_return_passes(self):
        assert rc.compare_field("return_1y", -25.13, -23.86)["status"] == "OK"

    def test_the_wrong_close_would_have_failed(self):
        """RSDFIN carried 152.44 in historical_valuation against a true close
        of 96.15 - a 58% error driving market cap, multiples and upside."""
        assert rc.compare_field("price", 152.44, 96.15)["status"] == "FAIL"

    def test_a_stale_by_days_price_warns_before_it_fails(self):
        """SUNTECK's cmp of 300.00 against a 296.20 close is small enough to
        miss by eye and large enough to move every derived figure."""
        assert rc.compare_field("price", 300.0, 296.2)["status"] == "WARN"

    def test_multiples_tolerate_a_different_earnings_basis(self):
        """360ONE PE 39.14 against 38.06, AAVAS 16.60 against 15.85. Both are
        correct; vendors compute TTM differently."""
        assert rc.compare_field("pe", 39.1412, 38.06)["status"] == "OK"
        assert rc.compare_field("pe", 16.5957, 15.85)["status"] == "OK"

    def test_a_genuinely_wrong_multiple_still_fails(self):
        assert rc.compare_field("pe", 13.76, 20.95)["status"] == "FAIL"

    def test_returns_are_compared_in_percentage_points(self):
        """A relative test near zero reports enormous errors for trivial gaps:
        0.1 against 0.2 is a 100% relative difference and 0.1 points."""
        assert rc.compare_field("return_1y", 0.1, 0.2)["status"] == "OK"

    def test_a_missing_value_is_not_a_divergence(self):
        assert rc.compare_field("pb", None, 1.2)["status"] == "SKIPPED"
        assert rc.compare_field("pb", 1.2, None)["status"] == "SKIPPED"

    def test_a_zero_reference_cannot_be_divided_by(self):
        assert rc.compare_field("price", 10.0, 0)["status"] == "SKIPPED"

    def test_an_unknown_field_is_declared_unchecked(self):
        assert rc.compare_field("mystery", 1, 2)["status"] == "UNCHECKED"


class TestSymbolRollup:
    def test_one_failing_field_fails_the_symbol(self):
        out = rc.compare_symbol("SUNTECK",
                                {"price": 294.25, "pe": 21.5, "return_1y": 23.1},
                                {"price": 296.2, "pe": 20.4, "return_1y": -23.86})
        assert out["status"] == "FAIL"
        assert out["failed_fields"] == ["return_1y"]

    def test_agreement_reads_ok(self):
        out = rc.compare_symbol("AAVAS", {"pe": 16.6, "pb": 2.2}, {"pe": 15.85, "pb": 2.16})
        assert out["status"] == "OK"


class TestReconcile:
    def test_summarises_and_orders_worst_first(self):
        ours = {"A": {"price": 100.0}, "B": {"price": 100.0}, "C": {"price": 100.0}}
        ref = {"A": {"price": 100.0}, "B": {"price": 101.5}, "C": {"price": 200.0}}
        out = rc.reconcile(ours, ref)
        assert out["ok"] is False
        assert out["failed"] == 1 and out["warned"] == 1
        assert out["divergences"][0]["symbol"] == "C"

    def test_a_symbol_the_reference_lacks_is_reported_not_counted_as_agreement(self):
        """Silence from the reference is not confirmation."""
        out = rc.reconcile({"A": {"price": 1.0}, "ZZZ": {"price": 1.0}},
                           {"A": {"price": 1.0}})
        assert out["not_in_reference"] == ["ZZZ"]
        assert out["compared"] == 1

    def test_symbols_match_case_insensitively(self):
        out = rc.reconcile({"aaa": {"price": 100.0}}, {"AAA": {"price": 100.0}})
        assert out["compared"] == 1 and out["ok"] is True

    def test_full_agreement_says_so_plainly(self):
        out = rc.reconcile({"A": {"price": 10.0, "pe": 20.0}},
                           {"A": {"price": 10.0, "pe": 20.0}})
        assert out["ok"] is True
        assert "agrees" in out["verdict"]

    def test_per_field_counts_show_where_the_problem_is(self):
        ours = {"A": {"price": 100.0, "pe": 20.0}, "B": {"price": 100.0, "pe": 20.0}}
        ref = {"A": {"price": 200.0, "pe": 20.0}, "B": {"price": 300.0, "pe": 20.0}}
        out = rc.reconcile(ours, ref)
        assert out["by_field"]["price"]["FAIL"] == 2
        assert out["by_field"]["pe"]["OK"] == 2


class TestRun:
    def test_a_reference_outage_fails_closed(self, monkeypatch):
        monkeypatch.setattr(rc, "desk_values", lambda limit=60: {"A": {"price": 1.0}})

        def _boom(_symbols):
            raise RuntimeError("vendor down")

        out = rc.run(_boom)
        assert out["ok"] is False and out["error"] == "reference_unavailable"

    def test_no_desk_values_fails_closed(self, monkeypatch):
        monkeypatch.setattr(rc, "desk_values", lambda limit=60: {})
        assert rc.run(lambda s: {})["error"] == "no_desk_values"

    def test_the_loader_is_asked_only_for_symbols_we_hold(self, monkeypatch):
        monkeypatch.setattr(rc, "desk_values",
                            lambda limit=60: {"B": {"price": 1.0}, "A": {"price": 1.0}})
        seen = {}

        def _loader(symbols):
            seen["symbols"] = list(symbols)
            return {}

        rc.run(_loader)
        assert seen["symbols"] == ["A", "B"], "sorted, and only ours"
