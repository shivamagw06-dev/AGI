import copy, tempfile, unittest, urllib.error
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from options_lab import paper_agents as p, spread_agents as s, yahoo_news as y, groww_observer as g
from test_spread_agents import enter, rows, NOW

class QuoteWaitTests(unittest.TestCase):
    def test_fresh_skew_waits_without_fill_then_resumes(self):
        state,a=enter();cash=a['cash'];equity=a['equity']
        at=NOW+timedelta(seconds=3);rr=rows(at)
        rr[1]['quote_at']=(NOW+timedelta(seconds=1)).isoformat()
        s.advance(state,rr,at,True,recover_gaps=True)
        self.assertFalse(a['blocked']);self.assertIsNotNone(a['position'])
        self.assertEqual((a['cash'],a['equity'],a['trades']),(cash,equity,[]))
        self.assertIn('synchronised',a['status'])
        at+=timedelta(seconds=1)
        s.advance(state,rows(at),at,True,recover_gaps=True)
        self.assertFalse(a['blocked']);self.assertIsNotNone(a['position']);self.assertFalse(a['trades'])
        self.assertEqual(a['events'][-1]['kind'],'quote_resumed')

    def test_continuous_skew_is_bounded_and_recovery_is_labelled(self):
        state,a=enter()
        for second in range(3,8):
            at=NOW+timedelta(seconds=second);rr=rows(at)
            rr[1]['quote_at']=(at-timedelta(seconds=2)).isoformat()
            s.advance(state,rr,at,True,recover_gaps=True)
        self.assertTrue(a['blocked']);self.assertFalse(a['trades'])
        at+=timedelta(seconds=1);s.advance(state,rows(at),at,True,recover_gaps=True)
        self.assertEqual(a['trades'][0]['evidence_status'],'data_gap_recovery')

    def test_thin_missing_or_stale_leg_never_uses_skew_grace(self):
        for failure in ('missing','stale','thin'):
            state,a=enter();at=NOW+timedelta(seconds=2);rr=rows(at)
            if failure=='missing':rr=rr[:1]
            elif failure=='stale':rr[1]['quote_at']=(at-timedelta(seconds=6)).isoformat()
            else:rr[1]['bid_size']=0
            s.advance(state,rr,at,True,recover_gaps=True)
            self.assertTrue(a['blocked']);self.assertFalse(a['trades'])

    def test_held_exit_does_not_require_entry_eligible_chain(self):
        state,a=enter();at=NOW+timedelta(seconds=2);rr=rows(at)
        expiry=(NOW.date()+timedelta(days=1)).isoformat()
        for r in rr:r['expiry']=expiry
        for leg in a['position']['legs']:leg['expiry']=expiry
        s.advance(state,rr,at,True,recover_gaps=True)
        self.assertFalse(a['blocked']);self.assertFalse(a['trades'])

    def test_groww_diagnostics_redact_exception_and_old_connection(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.e,'root',return_value=Path(d)):
            g.e.write('groww_stream',{'connection_verified_at':'old'})
            g.stage('index_quote');g.record_failure(urllib.error.HTTPError('https://private/?token=secret',401,'secret',{},None))
            state=g.e.read('groww_stream')
            self.assertIsNone(state['connection_verified_at'])
            self.assertIn('index_quote failed (HTTP 401)',state['error'])
            self.assertNotIn('secret',str(state))

    def test_yahoo_removed_endpoint_backs_off_for_day(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'paths',return_value=(Path(d)/'source',Path(d)/'paper')):
            calls=[]
            def get():
                calls.append(1)
                raise urllib.error.HTTPError(y.URL,404,'missing',{},None)
            first=y.poll(now=NOW,get=get)
            y.poll(now=NOW+timedelta(hours=1),get=get)
            self.assertFalse(first['available']);self.assertEqual(len(calls),1)
            self.assertEqual(p.timestamp(first['next_attempt_at']),NOW+timedelta(days=1))
