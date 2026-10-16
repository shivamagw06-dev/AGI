"""The canonical read: what a client sees when today's refresh did not work.

The old read already served yesterday's values rather than nulls. What it never
did was say so, and a stale number presented as current is worse than one
labelled stale, because nobody can tell.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_canon_"))

from institutional_warehouse import db, gateway  # noqa: E402
from valuation_ratios import canonical as c  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _company(symbol="AAA", sector=None):
    gateway.write("company_master",
                  [{"symbol": symbol, "isin": "INE001A01001", "company_id": symbol,
                    "company_name": symbol, **({"sector": sector} if sector else {})}],
                  source="test", actor="t", reason="seed")


def _snapshot(symbol, date, **ratios):
    rows = [{"company_id": symbol, "symbol": symbol, "isin": "INE001A01001",
             "ratio_name": name, "company_value": value,
             "reported_date": date, "snapshot_id": f"upstox-{date}-{symbol}"}
            for name, value in ratios.items() if value is not None]
    gateway.write("valuation_ratios", rows, source="upstox", actor="t", reason="seed")


ALL = {"pe": 18.5, "pb": 2.3, "roa": 8.0, "roe": 16.1, "roce": 19.0, "ev_ebitda": 11.0}


class TestFresh:
    def test_todays_snapshot_is_fresh_throughout(self):
        _company()
        _snapshot("AAA", "2026-08-21", **ALL)
        out = c.canonical_ratios("AAA", reference_date="2026-08-21")
        assert out["status"] == c.FRESH
        assert out["as_of"] == "2026-08-21"
        assert {m["status"] for m in out["metrics"].values()} == {c.FRESH}


class TestStale:
    def test_yesterdays_values_are_served_not_nulls(self):
        """The case this exists for: today's call timed out, and the client
        should still see numbers - labelled."""
        _company()
        _snapshot("AAA", "2026-08-20", **ALL)
        out = c.canonical_ratios("AAA", reference_date="2026-08-25")
        assert out["status"] == c.STALE
        assert out["as_of"] == "2026-08-20"
        assert out["metrics"]["pe"]["value"] == 18.5
        assert out["metrics"]["pe"]["status"] == c.STALE

    def test_a_failed_refresh_does_not_erase_the_older_snapshot(self):
        _company()
        _snapshot("AAA", "2026-08-20", **ALL)
        # Today's sweep failed, so it wrote nothing at all.
        out = c.canonical_ratios("AAA", reference_date="2026-08-25")
        assert out["metrics"]["roe"]["value"] == 16.1

    def test_the_newest_valid_row_wins_not_the_newest_row(self):
        """A row exists only when a value was collected, so these differ exactly
        when something went wrong."""
        _company()
        _snapshot("AAA", "2026-08-19", pe=17.0)
        _snapshot("AAA", "2026-08-21", pe=18.5)
        out = c.canonical_ratios("AAA", reference_date="2026-08-21")
        assert out["metrics"]["pe"]["value"] == 18.5


class TestPerMetricFreshness:
    def test_one_stale_metric_does_not_make_the_others_stale(self):
        _company()
        _snapshot("AAA", "2026-08-10", ev_ebitda=11.0)
        _snapshot("AAA", "2026-08-21", pe=18.5, pb=2.3, roa=8.0, roe=16.1, roce=19.0)
        out = c.canonical_ratios("AAA", reference_date="2026-08-21")
        assert out["metrics"]["pe"]["status"] == c.FRESH
        assert out["metrics"]["ev_ebitda"]["status"] == c.STALE
        assert out["status"] == c.PARTIAL_VALID

    def test_each_metric_carries_its_own_date(self):
        _company()
        _snapshot("AAA", "2026-08-10", ev_ebitda=11.0)
        _snapshot("AAA", "2026-08-21", pe=18.5)
        out = c.canonical_ratios("AAA", reference_date="2026-08-21")
        assert out["metrics"]["pe"]["as_of"] == "2026-08-21"
        assert out["metrics"]["ev_ebitda"]["as_of"] == "2026-08-10"
        assert out["oldest_as_of"] == "2026-08-10"


class TestNotApplicable:
    def test_a_bank_with_no_roce_is_fresh_not_degraded(self):
        """Deposits are a bank's raw material; there is no enterprise value net
        of debt and no capital employed in the industrial sense. Absent forever
        is not stale."""
        _company("HDFCBANK", sector="Financials")
        _snapshot("HDFCBANK", "2026-08-21", pe=18.5, pb=2.3, roa=8.0, roe=16.1)
        out = c.canonical_ratios("HDFCBANK", reference_date="2026-08-21")
        assert out["metrics"]["roce"]["status"] == c.NOT_APPLICABLE
        assert out["metrics"]["ev_ebitda"]["status"] == c.NOT_APPLICABLE
        assert out["status"] == c.FRESH, "a bank must not read as degraded every day"

    def test_a_manufacturer_missing_roce_is_a_gap(self):
        _company("WIDGETCO", sector="Industrials")
        _snapshot("WIDGETCO", "2026-08-21", pe=18.5, pb=2.3, roa=8.0, roe=16.1)
        out = c.canonical_ratios("WIDGETCO", reference_date="2026-08-21")
        assert out["metrics"]["roce"]["status"] == c.UNAVAILABLE
        assert out["status"] == c.PARTIAL_VALID


class TestIneligible:
    def test_an_etf_is_ineligible_not_unavailable(self):
        """UNAVAILABLE implies the number exists and we failed to get it."""
        gateway.write("company_master",
                      [{"symbol": "NV20BEES", "isin": "INE9", "company_id": "NV20BEES",
                        "company_name": "Nippon NV20 BeES"}],
                      source="test", actor="t", reason="seed")
        out = c.canonical_ratios("NV20BEES")
        assert out["status"] == c.INELIGIBLE
        assert out["metrics"] == {}


class TestNothingAtAll:
    def test_a_company_never_collected_is_unavailable(self):
        _company("NEWCO")
        out = c.canonical_ratios("NEWCO", reference_date="2026-08-21")
        assert out["status"] == c.UNAVAILABLE
        assert out["as_of"] is None
        assert all(m["value"] is None for m in out["metrics"].values())

    def test_every_metric_is_present_in_the_answer_even_when_absent(self):
        """A caller should not have to know which keys might be missing."""
        _company("NEWCO")
        out = c.canonical_ratios("NEWCO", reference_date="2026-08-21")
        assert set(out["metrics"]) == {"pe", "pb", "roa", "roe", "roce", "ev_ebitda"}
