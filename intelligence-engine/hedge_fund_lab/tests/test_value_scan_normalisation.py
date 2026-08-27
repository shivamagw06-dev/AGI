"""Regression tests for the Value screen's multiple normalisation.

Confirmed against production on 2026-08-19: every visible row on the Value
screen carried ``normalization_required`` with EV/EBITDA between 1.0 and 2.8.
ASHOKA read 1.03 where the real multiple is roughly 4-5x. Three separate
defects combined to put those rows at the top of the screen:

1. ``_SANE_BOUNDS`` admitted EV/EBITDA down to 1.0, so impossible multiples
   passed the sanity gate.
2. ``normalization_required`` was ``metric == "ev_ebitda"`` — true for every
   EV/EBITDA row regardless of value, so the flag carried no information.
3. The screen sorted ascending by discount, which ranks the most extreme and
   therefore most likely erroneous readings first.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import scanner
from hedge_fund_lab.scanner import (
    _SANE_BOUNDS,
    _sane,
    _scan_value,
    _suspect_multiple,
)


@pytest.fixture(autouse=True)
def _force_ev_ebitda_lens(monkeypatch):
    """_primary_metric resolves through the sector lens and falls back to "pe"
    for an unknown industry, which would make these fixtures test nothing."""
    monkeypatch.setattr(scanner, "_primary_metric", lambda _dna: "ev_ebitda")


def _company(symbol, industry, metric_value, *, roe=18.0, metric="ev_ebitda"):
    return {
        "ticker": symbol,
        "symbol": symbol,
        "company_name": symbol,
        "primary_industry": industry,
        "primary_sector": "Industrials",
        "industry_dna": industry,
        "market_cap": 5.0e9,
        "roe": roe,
        metric: metric_value,
    }


class TestSaneBounds:
    def test_impossible_ev_ebitda_is_rejected(self):
        """1.03x is not a cheap company; it is a broken denominator."""
        assert _sane(_company("ASHOKA", "Construction", 1.03), "ev_ebitda") is None
        assert _sane(_company("BIRLACABLE", "Cables", 2.78), "ev_ebitda") is None

    def test_plausible_ev_ebitda_survives(self):
        assert _sane(_company("REAL", "Construction", 8.4), "ev_ebitda") == 8.4

    def test_floor_is_above_the_impossible_range(self):
        low, high = _SANE_BOUNDS["ev_ebitda"]
        assert low >= 3.0, "a solvent listed company does not trade below ~3x EBITDA"
        assert high <= 80.0


class TestSuspectFlagging:
    def test_flag_is_not_true_for_every_ev_ebitda(self):
        """The old rule flagged the metric; the new one flags the value."""
        assert _suspect_multiple("ev_ebitda", 3.5) is True
        assert _suspect_multiple("ev_ebitda", 8.4) is False

    def test_unknown_metric_is_never_suspect(self):
        assert _suspect_multiple("ev_sales", 0.1) is False

    def test_missing_value_is_not_suspect(self):
        assert _suspect_multiple("ev_ebitda", None) is False


class TestValueScanRanking:
    """Verified candidates must outrank flagged ones."""

    def _run(self):
        universe = [
            # Plausible discount, healthy returns — should rank first.
            _company("CLEAN", "Construction", 6.0, roe=22.0),
            # Inside the band but suspect: ranks below the verified row.
            _company("SUSPECT", "Construction", 3.2, roe=20.0),
            # Peers establishing the median.
            *[_company(f"PEER{i}", "Construction", 12.0, roe=15.0) for i in range(6)],
        ]
        medians = {"Construction": {"count": 8, "ev_ebitda": 12.0, "roe": 15.0}}
        return _scan_value(universe, medians, 10)

    def test_a_plausible_multiple_is_actually_validated(self):
        """Under the old rule every EV/EBITDA row was flagged, so this failed."""
        rows = {r["ticker"]: r for r in self._run()}
        assert "CLEAN" in rows, "a plausible discounted company must survive the screen"
        assert rows["CLEAN"]["validation_status"] == "screen_validated"

    def test_verified_rows_rank_above_flagged(self):
        rows = self._run()
        statuses = [r["validation_status"] for r in rows]
        assert "screen_validated" in statuses, "screen produced no verified candidate at all"
        assert "normalization_required" in statuses, "fixture must contain a flagged row"
        assert statuses.index("screen_validated") < statuses.index("normalization_required")

    def test_impossible_multiples_never_appear(self):
        rows = self._run()
        for row in rows:
            if row["metric"] == "ev_ebitda":
                assert row["value"] >= _SANE_BOUNDS["ev_ebitda"][0]

    def test_relative_multiple_matches_the_published_formula(self):
        """R = m / median, the identity the desk prints beside the table."""
        for row in self._run():
            expected = round(row["value"] / row["industry_median"], 2)
            assert row["relative_multiple"] == expected

    def test_discount_matches_the_published_formula(self):
        """D = (m / median) - 1, expressed in percent."""
        for row in self._run():
            expected = round(((row["value"] / row["industry_median"]) - 1.0) * 100.0, 1)
            assert row["discount_pct"] == expected
