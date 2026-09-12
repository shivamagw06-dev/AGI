"""Expired-instrument reads, exercised without touching Upstox."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import expired_history as eh
from options_lab.upstox_live import UpstoxLiveError


CONTRACTS = [
    {"instrument_key": "NSE_FO|44120", "trading_symbol": "NIFTY 24000 CE",
     "expiry": "2026-04-24", "strike_price": 24000, "instrument_type": "CE",
     "lot_size": 75, "underlying_key": "NSE_INDEX|Nifty 50"},
    {"instrument_key": "NSE_FO|44121", "trading_symbol": "NIFTY 24000 PE",
     "expiry": "2026-04-24", "strike_price": 24000, "instrument_type": "PE",
     "lot_size": 75, "underlying_key": "NSE_INDEX|Nifty 50"},
    # A row with no key cannot be fetched later, so it must not become a contract.
    {"instrument_key": "", "trading_symbol": "broken", "strike_price": 1},
]

# Upstox answers newest first.
CANDLES = {"candles": [
    ["2026-04-24T15:15:00+05:30", 12.0, 13.0, 11.0, 11.5, 900, 4100],
    ["2026-04-24T15:00:00+05:30", 10.0, 12.5, 10.0, 12.0, 1200, 4000],
]}


class ListCalls(unittest.TestCase):
    def test_expiries_come_back_sorted_oldest_first(self):
        with mock.patch.object(eh, "_request",
                               return_value=["2026-04-24", "2026-01-30", "2026-03-27"]):
            self.assertEqual(eh.list_expiries(token="t"),
                             ["2026-01-30", "2026-03-27", "2026-04-24"])

    def test_contracts_without_a_key_are_dropped(self):
        # Keeping one would put a row in the plan that no candle call can serve.
        with mock.patch.object(eh, "_request", return_value=CONTRACTS):
            out = eh.list_contracts("2026-04-24", token="t")
        self.assertEqual(len(out), 2)
        self.assertEqual({c.option_type for c in out}, {"CE", "PE"})
        self.assertTrue(all(c.is_option for c in out))

    def test_strike_and_lot_survive_as_numbers(self):
        with mock.patch.object(eh, "_request", return_value=CONTRACTS):
            call = eh.list_contracts("2026-04-24", token="t")[0]
        self.assertEqual(call.strike, 24000.0)
        self.assertEqual(call.lot_size, 75)


class Candles(unittest.TestCase):
    def test_candles_are_returned_oldest_first(self):
        # Upstox sends newest first. A caller walking the list forward is
        # walking time forward only because this reverses them.
        with mock.patch.object(eh, "_request", return_value=CANDLES):
            rows = eh.candles("NSE_FO|44120", "2026-04-24", "2026-04-24", token="t")
        self.assertEqual(rows[0][0], "2026-04-24T15:00:00+05:30")
        self.assertEqual(rows[-1][0], "2026-04-24T15:15:00+05:30")

    def test_open_interest_is_the_seventh_field(self):
        with mock.patch.object(eh, "_request", return_value=CANDLES):
            rows = eh.candles("NSE_FO|44120", "2026-04-24", "2026-04-24", token="t")
        self.assertEqual(len(rows[0]), 7)
        self.assertEqual(rows[0][6], 4000)

    def test_an_unknown_interval_is_refused_before_the_call(self):
        with self.assertRaises(ValueError):
            eh.candles("NSE_FO|44120", "2026-04-24", "2026-04-24",
                       interval="7minute", token="t")

    def test_the_instrument_key_is_url_encoded_into_the_path(self):
        seen = {}

        def capture(url, token, timeout=30):
            seen["url"] = url
            return CANDLES

        with mock.patch.object(eh, "_request", side_effect=capture):
            eh.candles("NSE_FO|4 41|20", "2026-04-01", "2026-04-24", token="t")
        # A raw pipe or space in the path would build a different URL than
        # intended, and Upstox would answer about the wrong instrument or 404.
        self.assertIn("NSE_FO%7C4%2041%7C20", seen["url"])
        self.assertNotIn("NSE_FO|4 41|20", seen["url"])

    def test_dates_go_into_the_path_as_to_then_from(self):
        seen = {}

        def capture(url, token, timeout=30):
            seen["url"] = url
            return CANDLES

        with mock.patch.object(eh, "_request", side_effect=capture):
            eh.candles("K", "2026-04-01", "2026-04-24", token="t")
        # Reversing these silently returns nothing rather than failing.
        self.assertTrue(seen["url"].endswith("/15minute/2026-04-24/2026-04-01"))


class Probe(unittest.TestCase):
    def test_a_plan_refusal_is_reported_as_a_stage_not_a_crash(self):
        with mock.patch.object(eh, "load_access_token", return_value="t"), \
             mock.patch.object(eh, "list_expiries",
                               side_effect=UpstoxLiveError("HTTP 403: not authorised")):
            out = eh.probe()
        self.assertFalse(out["ok"])
        self.assertEqual(out["stage"], "expiries")
        self.assertIn("403", out["error"])

    def test_only_future_expiries_is_a_failure_because_there_is_no_history(self):
        with mock.patch.object(eh, "load_access_token", return_value="t"), \
             mock.patch.object(eh, "list_expiries", return_value=["2099-01-01"]):
            out = eh.probe()
        self.assertFalse(out["ok"])
        self.assertEqual(out["stage"], "expiries")

    def test_a_working_account_reports_the_sample_it_actually_read(self):
        with mock.patch.object(eh, "load_access_token", return_value="t"), \
             mock.patch.object(eh, "list_expiries",
                               return_value=["2020-01-02", "2020-01-09"]), \
             mock.patch.object(eh, "list_contracts", return_value=[
                 eh.ExpiredContract("NSE_FO|1", "NIFTY 24000 CE", "2020-01-09",
                                    24000.0, "CE", 75, eh.NIFTY_KEY)]), \
             mock.patch.object(eh, "candles", return_value=CANDLES["candles"]):
            out = eh.probe()
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["stage"], "complete")
        self.assertEqual(out["expiries_past"], 2)
        self.assertTrue(out["has_open_interest"])


if __name__ == "__main__":
    unittest.main()
