import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from options_lab.paper_agents import fresh_state, step, direction, valid_quote, control, dashboard, tick, backtest
from options_lab.store import OptionEvidenceStore


def quote(at,spot=25000,bid=99,ask=100,lot=65,side='CE'):
    return dict(captured_at=f'2026-09-28T{at}:00+05:30',underlying_key='NSE_INDEX|Nifty 50',provider='upstox',spot=spot,expiry='2026-10-06',instrument_key='NSE_FO|123',option_type=side,strike=25000,lot_size=lot,bid=bid,ask=ask,volume=10000,oi=1000)


def setup():
    state=fresh_state()
    for t,s in [('09:15',25000),('09:30',25010),('09:45',25005),('10:00',25060)]:
        step(state,[quote(t,s)])
    return state


class PaperTests(unittest.TestCase):
    def test_signal_waits_for_next_quote_and_duplicate_is_noop(self):
        state=setup();a=state['agents']['opening_range']
        self.assertIsNotNone(a['pending']);self.assertIsNone(a['position'])
        before=copy.deepcopy(state);step(state,[quote('10:00',25100)])
        self.assertEqual(state,before)
        step(state,[quote('10:15',25080)])
        self.assertEqual(a['position']['quantity'],65)
        self.assertAlmostEqual(a['position']['entry_price'],100.5)
        self.assertLess(a['equity'],100000)

    def test_repeated_collections_cannot_accelerate_strategy(self):
        state=setup()
        prior=copy.deepcopy(state)
        q=quote('10:00',25100)
        q['captured_at']='2026-09-28T10:00:45+05:30'
        step(state,[q])
        self.assertEqual(prior,state)
        self.assertIsNone(state['agents']['opening_range']['position'])
        step(state,[quote('10:15',25080)])
        self.assertIsNotNone(state['agents']['opening_range']['position'])

    def test_opening_range_needs_three_distinct_windows(self):
        history=[dict(minute=m,spot=25000) for m in [555,556,585]]
        self.assertIsNone(direction('opening_range',history,25200))

    def test_pause_before_activation_is_safe(self):
        with tempfile.TemporaryDirectory() as d,patch('options_lab.paper_agents.paths',return_value=(Path(d)/'source.sqlite',Path(d)/'paper.sqlite')):
            self.assertFalse(control('pause')['enabled'])

    def test_exit_uses_bid_costs_and_actual_stop_gap(self):
        state=setup();step(state,[quote('10:15',25080)])
        step(state,[quote('10:30',25000,bid=60,ask=61)])
        a=state['agents']['opening_range'];t=a['trades'][0]
        self.assertEqual(t['reason'],'Daily loss limit')
        self.assertAlmostEqual(t['exit_price'],59.7)
        self.assertLess(t['pnl'],-2600)
        self.assertAlmostEqual(a['cash']-100000,t['pnl'],places=2)
        self.assertGreater(a['max_drawdown'],2600)

    def test_no_fabricated_exit_after_missing_quotes(self):
        state=setup();step(state,[quote('10:15',25080)])
        step(state,[quote('11:00',25000)])
        a=state['agents']['opening_range']
        self.assertTrue(a['blocked']);self.assertIsNotNone(a['position']);self.assertFalse(a['trades'])

    def test_stale_source_cannot_open_live_trade(self):
        state=setup()
        step(state,[quote('10:15',25080)],wall_now=datetime(2026,9,28,8,tzinfo=timezone.utc))
        self.assertIsNone(state['agents']['opening_range']['position'])

    def test_budget_never_splits_or_overbuys_lots(self):
        state=setup();step(state,[quote('10:15',25080,bid=499,ask=500)])
        self.assertIsNone(state['agents']['opening_range']['position'])

    def test_missing_opening_quotes_do_not_invent_range(self):
        state=fresh_state()
        for t,s in [('10:00',25000),('10:15',25010),('10:30',25200)]:
            step(state,[quote(t,s)])
        self.assertIsNone(state['agents']['opening_range']['pending'])

    def test_invalid_liquidity(self):
        for change in [dict(bid=101),dict(lot_size=0),dict(lot_size=1.5),dict(ask=float('nan')),dict(volume=0),dict(oi=None),dict(bid=50)]:
            q=quote('10:00');q.update(change);self.assertFalse(valid_quote(q))

    def test_expiry_day_and_other_indices_excluded(self):
        state=setup();state['agents']['opening_range']['pending']=None
        q=quote('10:15',25200);q['expiry']='2026-09-28';step(state,[q])
        self.assertIsNone(state['agents']['opening_range']['pending'])
        prior=copy.deepcopy(state);q=quote('10:30');q['underlying_key']='NSE_INDEX|Nifty Bank';step(state,[q])
        self.assertEqual(prior,state)

    def test_mean_reversion_prior_only(self):
        history=[dict(spot=s) for s in [25000,25010,25000,25005,25000,25010]]
        self.assertEqual(direction('mean_reversion',history,24900),'CE')
        self.assertEqual(direction('mean_reversion',history,25100),'PE')
        self.assertIsNone(direction('mean_reversion',history[:3],24900))

    def test_pause_still_observes_exits(self):
        state=setup();step(state,[quote('10:15',25080)])
        step(state,[quote('10:30',25000,bid=75,ask=76)],allow_entries=False)
        self.assertEqual(len(state['agents']['opening_range']['trades']),1)

    def test_storage_start_pause_and_replay_are_separate(self):
        with tempfile.TemporaryDirectory() as d,patch('options_lab.paper_agents.paths',return_value=(Path(d)/'source.sqlite',Path(d)/'paper.sqlite')):
            result=control('start');self.assertTrue(result['enabled'])
            self.assertEqual(result['live']['agents']['opening_range']['cash'],100000)
            self.assertEqual(backtest('2026-09-01','2026-09-02')['status'],'no_data')
            self.assertIsNone(dashboard()['live']['last_at'])
            self.assertFalse(control('pause')['enabled'])
            with self.assertRaises(ValueError):control('real')

    def test_replay_no_future_or_oversized_ranges(self):
        with self.assertRaises(ValueError):backtest('2026-01-01','2026-09-28')
        with self.assertRaises(ValueError):backtest('2036-09-01','2036-09-02')

    def test_persisted_replay_and_forward_cursor(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d,patch('options_lab.paper_agents.paths',return_value=(Path(d)/'source.sqlite',Path(d)/'paper.sqlite')):
            rows=[quote(t,s) for t,s in [('09:15',25000),('09:30',25010),('09:45',25005),('10:00',25060),('10:15',25080)]]
            rows.append(quote('10:30',25000,bid=75,ask=76))
            with sqlite3.connect(Path(d)/'source.sqlite') as db:
                columns=list(rows[0])
                db.execute('CREATE TABLE option_snapshots ('+','.join(columns)+',local_date)')
                for r in rows:
                    db.execute('INSERT INTO option_snapshots VALUES ('+','.join('?' for _ in range(len(columns)+1))+')',list(r.values())+['2026-09-28'])
            replay=backtest('2026-09-28','2026-09-28')
            self.assertEqual(replay['agents']['opening_range']['closed_trades'],1)
            control('start')
            with sqlite3.connect(Path(d)/'paper.sqlite') as db:
                db.execute("UPDATE sessions SET started_at='2026-09-28T00:00:00+00:00'")
            # Frozen now is within freshness bounds for the final batch. Older
            # observations can supply context but may never open a live fill.
            with patch('options_lab.paper_agents.datetime') as clock:
                clock.now.return_value=datetime(2026,9,28,5,1,tzinfo=timezone.utc)
                clock.fromisoformat.side_effect=datetime.fromisoformat
                tick()
                first=dashboard()['live']
                tick()
                self.assertEqual(first,dashboard()['live'])
                self.assertEqual(first['agents']['opening_range']['closed_trades'],0)

if __name__=='__main__':unittest.main()
