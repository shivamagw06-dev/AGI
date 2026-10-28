import copy, tempfile, unittest, urllib.error
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from options_lab import paper_agents as p, spread_agents as s, news_monitor as n
from test_spread_agents import enter, rows, NOW

class RuntimeRecoveryTests(unittest.TestCase):
    def test_basket_recovery_requires_both_quotes_and_locks_day(self):
        state,a=enter();original=copy.deepcopy(a['position'])
        at=NOW+timedelta(seconds=10)
        s.advance(state,[],at,True,recover_gaps=True)
        self.assertTrue(a['blocked']);self.assertEqual(a['position'],original)
        s.advance(state,rows(at+timedelta(seconds=1))[:1],at+timedelta(seconds=1),True,recover_gaps=True)
        self.assertIsNotNone(a['position'])
        at+=timedelta(seconds=2)
        s.advance(state,rows(at),at,True,recover_gaps=True)
        self.assertIsNone(a['position']);self.assertEqual(len(a['trades']),1)
        self.assertEqual(a['trades'][0]['evidence_status'],'data_gap_recovery')
        self.assertEqual(a['trades'][0]['entry_at'],original['entry_at'])
        s.advance(state,rows(at+timedelta(seconds=1)),at+timedelta(seconds=1),True,recover_gaps=True)
        self.assertIn('locked',a['status']);self.assertEqual(len(a['trades']),1)

    def test_exit_dte_is_not_entry_dte(self):
        q=rows()[0];q['expiry']=NOW.date().isoformat()
        self.assertFalse(s.usable(q,NOW));self.assertTrue(s.usable(q,NOW,entry=False))

    def test_legacy_recovery_preserves_history_and_uses_actual_bid(self):
        state=p.fresh_state();a=state['agents']['opening_range'];q=rows()[0]
        state.update(day=NOW.date().isoformat(),last_at=(NOW-timedelta(seconds=10)).isoformat())
        a.update(blocked=True,cash=93000,position=dict(instrument_key=q['instrument_key'],expiry=q['expiry'],strike=q['strike'],option_type=q['option_type'],entry_at=(NOW-timedelta(minutes=5)).isoformat(),entry_price=100,quantity=65,equity_before=100000))
        p.step(state,rows(),wall_now=NOW,interval_seconds=1,recover_gaps=True)
        self.assertIsNone(a['position']);self.assertEqual(len(a['trades']),1)
        self.assertAlmostEqual(a['trades'][0]['exit_price'],99*.995)
        p.step(state,rows(NOW+timedelta(seconds=1)),wall_now=NOW+timedelta(seconds=1),interval_seconds=1,recover_gaps=True)
        self.assertIn('locked',a['status'])

    def test_news_rate_limit_is_persisted_and_prevents_requests(self):
        with tempfile.TemporaryDirectory() as d, patch.object(p,'paths',return_value=(Path(d)/'source',Path(d)/'paper')),patch.object(n,'load_access_token',return_value='test'):
            calls=[]
            def get(*args):
                calls.append(1);raise urllib.error.HTTPError('https://api.upstox.com/v2/news',429,'limited',{},None)
            first=n.poll({'x':'x'},'test',now=NOW,get=get)
            second=n.poll({'x':'x'},'test',now=NOW+timedelta(seconds=60),get=get)
            self.assertEqual(len(calls),1);self.assertFalse(second['available'])
            self.assertEqual(first['next_attempt_at'],second['next_attempt_at'])

    def test_legacy_stale_or_undersized_recovery_never_fills(self):
        for change in ({'bid_size':0},{'quote_at':(NOW-timedelta(seconds=10)).isoformat()},{'strike':999}):
            state=p.fresh_state();a=state['agents']['opening_range'];q=rows()[0]
            state.update(day=NOW.date().isoformat(),last_at=(NOW-timedelta(seconds=10)).isoformat())
            a.update(blocked=True,cash=93000,position=dict(instrument_key=q['instrument_key'],expiry=q['expiry'],strike=q['strike'],option_type=q['option_type'],entry_at=(NOW-timedelta(minutes=5)).isoformat(),entry_price=100,quantity=65,equity_before=100000))
            q.update(change)
            p.step(state,[q],wall_now=NOW,interval_seconds=1,recover_gaps=True)
            self.assertIsNotNone(a['position']);self.assertEqual(a['trades'],[])
