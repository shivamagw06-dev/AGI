"""Deriving option observations from a bhavcopy, without fetching one."""

from __future__ import annotations

import math
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import nse_history as nh
from options_lab.engine import _price


TRADE = "2026-08-21"
EXPIRY = "2026-08-25"
SPOT = 24252.0
RATE = nh.DEFAULT_RATE_PCT / 100.0
T = 4 / 365.0


def option(strike, kind, close, *, volume=1000, oi=5000, doi=100,
           expiry=EXPIRY, symbol="NIFTY", tp="IDO"):
    return {
        "TradDt": TRADE, "TckrSymb": symbol, "XpryDt": expiry,
        "FinInstrmTp": tp, "OptnTp": kind, "StrkPric": str(strike),
        "OpnPric": str(close), "HghPric": str(close), "LwPric": str(close),
        "ClsPric": str(close), "SttlmPric": str(close),
        "TtlTradgVol": str(volume), "OpnIntrst": str(oi),
        "ChngInOpnIntrst": str(doi), "UndrlygPric": str(SPOT),
        "ISIN": "INE000A01001",
    }


def future(close, *, expiry=EXPIRY, symbol="NIFTY"):
    row = option(0, "", close, expiry=expiry, symbol=symbol, tp="IDF")
    row["OptnTp"] = ""
    return row


def chain_at(forward, vol, strikes):
    """A chain priced from a known forward and volatility, via Black-76."""
    rows = []
    for k in strikes:
        c = _price("call", forward, k, T, RATE, RATE, vol)
        p = _price("put", forward, k, T, RATE, RATE, vol)
        rows.append(option(k, "CE", round(c, 2)))
        rows.append(option(k, "PE", round(p, 2)))
    return rows


class ForwardDerivation(unittest.TestCase):
    def test_parity_recovers_the_forward_the_chain_was_priced_from(self):
        # If this drifts, every implied volatility in the warehouse drifts with it.
        rows = chain_at(24287.0, 0.15, [24100, 24200, 24300, 24400])
        fwd = nh.forward_for_expiry(rows)
        self.assertEqual(fwd.source, "parity")
        self.assertAlmostEqual(fwd.value, 24287.0, delta=1.0)

    def test_parity_beats_spot_which_is_what_makes_it_worth_the_work(self):
        rows = chain_at(24287.0, 0.15, [24200, 24300])
        fwd = nh.forward_for_expiry(rows)
        self.assertLess(abs(fwd.value - 24287.0), abs(SPOT - 24287.0))

    def test_the_chosen_strike_is_the_one_nearest_the_money(self):
        rows = chain_at(24287.0, 0.15, [23000, 24300, 25500])
        # 23000 and 25500 are deep in and out; parity there leans on a wing price.
        self.assertEqual(nh.forward_for_expiry(rows).strike, 24300)

    def test_a_future_is_used_when_no_strike_has_both_legs(self):
        rows = [option(24300, "CE", 70.0), future(24286.0)]
        fwd = nh.forward_for_expiry(rows)
        self.assertEqual(fwd.source, "future")
        self.assertEqual(fwd.value, 24286.0)

    def test_spot_is_the_last_resort_and_says_so(self):
        rows = [option(24300, "CE", 70.0)]
        fwd = nh.forward_for_expiry(rows)
        self.assertEqual(fwd.source, "spot")
        self.assertEqual(fwd.value, SPOT)

    def test_untraded_contracts_do_not_set_the_forward(self):
        # NSE still writes a close for a contract nobody traded. Letting those
        # set the forward would anchor the surface to NSE's settlement model.
        real = chain_at(24287.0, 0.15, [24300])
        ghost = [option(24000, "CE", 9999.0, volume=0),
                 option(24000, "PE", 0.05, volume=0)]
        fwd = nh.forward_for_expiry(real + ghost)
        self.assertAlmostEqual(fwd.value, 24287.0, delta=1.0)

    def test_expiry_day_has_no_forward_rather_than_a_fictitious_one(self):
        rows = chain_at(24287.0, 0.15, [24300])
        for r in rows:
            r["XpryDt"] = TRADE          # expires today: T = 0
        self.assertIsNone(nh.forward_for_expiry(rows))


class Records(unittest.TestCase):
    def test_implied_volatility_returns_what_the_chain_was_priced_at(self):
        rows = chain_at(24287.0, 0.18, [24200, 24300, 24400])
        recs = nh.option_records(rows, underlyings={"NIFTY"})
        self.assertTrue(recs)
        for r in recs:
            self.assertAlmostEqual(r["iv"], 18.0, delta=0.5)

    def test_untraded_rows_are_excluded_by_default(self):
        rows = chain_at(24287.0, 0.15, [24300]) + [option(99000, "CE", 0.05, volume=0)]
        strikes = {r["strike"] for r in nh.option_records(rows, underlyings={"NIFTY"})}
        self.assertNotIn(99000, strikes)

    def test_moneyness_is_measured_against_the_forward_not_spot(self):
        rows = chain_at(24287.0, 0.15, [24300])
        rec = nh.option_records(rows, underlyings={"NIFTY"})[0]
        self.assertAlmostEqual(rec["moneyness"], rec["strike"] / rec["forward"], places=6)
        self.assertAlmostEqual(rec["log_moneyness"],
                               math.log(rec["strike"] / rec["forward"]), places=6)
        self.assertNotAlmostEqual(rec["moneyness"], rec["strike"] / SPOT, places=4)

    def test_open_interest_and_its_change_survive_the_derivation(self):
        # These are the positioning study's raw material; losing them silently
        # would leave the columns present and always zero.
        rows = chain_at(24287.0, 0.15, [24300])
        for r in rows:
            r["OpnIntrst"], r["ChngInOpnIntrst"] = "13469820", "3683940"
        rec = nh.option_records(rows, underlyings={"NIFTY"})[0]
        self.assertEqual(rec["open_interest"], 13469820.0)
        self.assertEqual(rec["change_in_oi"], 3683940.0)

    def test_other_underlyings_are_filtered_out(self):
        rows = chain_at(24287.0, 0.15, [24300])
        other = chain_at(1000.0, 0.2, [1000])
        for r in other:
            r["TckrSymb"] = "RELIANCE"
        recs = nh.option_records(rows + other, underlyings={"NIFTY"})
        self.assertEqual({r["underlying"] for r in recs}, {"NIFTY"})

    def test_a_deep_wing_with_no_solvable_volatility_keeps_its_prices(self):
        # A row whose price sits outside the no-arbitrage bounds cannot yield an
        # IV. Dropping it would quietly bias any OI study toward the liquid core.
        rows = chain_at(24287.0, 0.15, [24300]) + [option(24350, "CE", 0.05)]
        recs = nh.option_records(rows, underlyings={"NIFTY"})
        wing = [r for r in recs if r["strike"] == 24350]
        self.assertEqual(len(wing), 1)
        self.assertEqual(wing[0]["close"], 0.05)


class YearFraction(unittest.TestCase):
    def test_days_to_expiry_are_calendar_days(self):
        self.assertAlmostEqual(
            nh.year_fraction(date(2026, 8, 21), date(2026, 8, 25)), 4 / 365)

    def test_today_and_the_past_are_zero_not_negative(self):
        self.assertEqual(nh.year_fraction(date(2026, 8, 25), date(2026, 8, 25)), 0.0)
        self.assertEqual(nh.year_fraction(date(2026, 8, 26), date(2026, 8, 25)), 0.0)


if __name__ == "__main__":
    unittest.main()
