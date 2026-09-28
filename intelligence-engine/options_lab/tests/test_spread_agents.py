import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from options_lab import spread_agents as s, paper_agents as p

NOW=datetime.fromisoformat('2026-09-28T10:15:00+05:30')

def quote(key,strike,side,bid,ask,now=NOW,iv=20):
    return dict(instrument_key=key,strike=strike,option_type=side,expiry='2026-10-06',
        lot_size=65,bid=bid,ask=ask,bid_size=650,ask_size=650,volume=10000,oi=1000,
        quote_at=now.isoformat(),captured_at=now.isoformat(),spot_at=now.isoformat(),
        provider='upstox',underlying_key='NSE_INDEX|Nifty 50',spot=25080,iv=iv)

def rows(now=NOW):
    return [quote('L',25100,'CE',99,100,now),quote('S',25150,'CE',79,80,now),
            quote('PS',24950,'PE',31.5,32,now),quote('PL',24900,'PE',9.7,10,now),
            quote('ATM',25100,'PE',100,101,now)]

def signal(name='trend_pullback'):
    return dict(side='CE',rv=8,bar_at=int(NOW.timestamp())-300)

def pending(state,name='trend_pullback',now=NOW):
    legs=s.select_legs(rows(now),signal(name),name,25080)
    state['agents'][name]['pending']=dict(legs=legs,signal_at=now.isoformat(),signal=signal(name))
    state['day']=now.date().isoformat();state['last_at']=now.isoformat()
    return state['agents'][name]

def enter(name='trend_pullback'):
    state=s.fresh();a=pending(state,name)
    s.advance(state,rows(NOW+timedelta(seconds=1)),NOW+timedelta(seconds=1),True)
    return state,a

class SpreadTests(unittest.TestCase):
    def test_fee_sides_and_components(self):
        buy=s.costs(10000,'BUY');sell=s.costs(10000,'SELL')
        self.assertEqual(buy['stt'],0);self.assertEqual(sell['stt'],15)
        self.assertAlmostEqual(buy['stamp'],.3);self.assertEqual(sell['stamp'],0)
        self.assertAlmostEqual(buy['exchange'],3.553)
        self.assertAlmostEqual(buy['total'],sum(v for k,v in buy.items() if k!='total'))

    def test_complete_candles_only_and_ohlc(self):
        state=s.fresh();start=NOW-timedelta(minutes=5)
        for sec in range(300):
            self.assertIsNone(s.candle_sample(state,start+timedelta(seconds=sec),25000+sec))
        closed=s.candle_sample(state,NOW,1)
        self.assertEqual(closed['open'],25000);self.assertEqual(closed['close'],25299)
        self.assertEqual(closed['high'],25299);self.assertEqual(closed['low'],25000)
        self.assertEqual(len(state['candles']),1)

    def test_missing_minute_and_midminute_start_do_not_fake_candles(self):
        state=s.fresh();start=NOW-timedelta(minutes=5)
        for sec in range(30,301):s.candle_sample(state,start+timedelta(seconds=sec),25000)
        self.assertFalse(state['candles'])
        state=s.fresh()
        for sec in range(301):
            if 100<=sec<120:continue
            s.candle_sample(state,start+timedelta(seconds=sec),25000)
        self.assertFalse(state['candles'])

    def test_signal_uses_closed_history_and_requires_pullback(self):
        closes=[25000,25005,25010,25015,25020,25025,25030,25035,25040,25045,25030,25080]
        bars=[dict(at=i*300,open=c,close=c,high=c+5,low=c-5) for i,c in enumerate(closes)]
        self.assertEqual(s.setup(bars,'trend_pullback')['side'],'CE')
        self.assertIsNone(s.setup(bars[:11],'trend_pullback'))
        bars[-2]['low']=25070
        self.assertIsNone(s.setup(bars,'trend_pullback'))
        bars[-2]['at']-=10
        self.assertIsNone(s.setup(bars,'volatility_credit'))

    def test_two_legs_same_expiry_and_correct_spread_direction(self):
        for name in s.NAMES:
            legs=s.select_legs(rows(),signal(name),name,25080)
            self.assertEqual([x['side'] for x in legs],['BUY','SELL'])
            self.assertLess(legs[0]['strike'],legs[1]['strike'])
            self.assertEqual(legs[0]['expiry'],legs[1]['expiry'])
        bearish=dict(side='PE',rv=8)
        rr=[quote('P1',25100,'PE',100,101),quote('P2',25050,'PE',79,80)]
        legs=s.select_legs(rr,bearish,'trend_pullback',25080)
        self.assertGreater(legs[0]['strike'],legs[1]['strike'])

    def test_credit_missing_or_low_iv_means_no_trade(self):
        for iv in (None,5,201):
            rr=rows()
            for r in rr:r['iv']=iv
            self.assertIsNone(s.select_legs(rr,signal(),'volatility_credit',25080))
        self.assertIsNone(s.select_legs(rows(),dict(side='CE',rv=30),'volatility_credit',25080))

    def test_debit_and_credit_pnl_reconcile_cash(self):
        for name in s.NAMES:
            state,a=enter(name);self.assertIsNotNone(a['position'])
            self.assertLess(a['equity'],100000);self.assertGreater(a['capital_reserved'],0)
            self.assertLessEqual(a['position']['max_loss'],2000)
            now=NOW+timedelta(seconds=2);rr=rows(now)
            for r in rr:
                if name=='trend_pullback' and r['instrument_key']=='L':r.update(bid=120,ask=121)
                if name=='volatility_credit' and r['instrument_key']=='PS':r.update(bid=11.8,ask=12)
            s.advance(state,rr,now,True)
            self.assertIsNone(a['position']);self.assertEqual(len(a['trades']),1)
            t=a['trades'][0];self.assertGreater(t['pnl'],0)
            self.assertAlmostEqual(a['cash']-100000,t['pnl'],places=2)
            self.assertEqual(a['capital_reserved'],0)
            self.assertEqual(len(t['exit_legs']),2)

    def test_all_or_none_entry_on_missing_stale_skew_depth_or_old_signal_quote(self):
        for failure in ('missing','stale','skew','depth','same','expiry','lot'):
            state=s.fresh();a=pending(state);now=NOW+timedelta(seconds=3);rr=rows(now)
            if failure=='missing':rr=[r for r in rr if r['instrument_key']!='S']
            if failure=='stale':rr[1]['quote_at']=(NOW-timedelta(seconds=10)).isoformat()
            if failure=='skew':rr[1]['quote_at']=(NOW+timedelta(seconds=1)).isoformat()
            if failure=='depth':rr[1]['bid_size']=1
            if failure=='same':rr[1]['quote_at']=NOW.isoformat()
            if failure=='expiry':rr[1]['expiry']='2026-10-13'
            if failure=='lot':rr[1]['lot_size']=75
            s.advance(state,rr,now,True)
            self.assertIsNone(a['position'],failure);self.assertEqual(a['cash'],100000)

    def test_missing_exit_freezes_both_legs_and_no_later_fabricated_fill(self):
        state,a=enter();now=NOW+timedelta(seconds=2)
        s.advance(state,[r for r in rows(now) if r['instrument_key']!='S'],now,True)
        self.assertTrue(a['blocked']);self.assertEqual(len(a['position']['legs']),2)
        s.advance(state,rows(now+timedelta(seconds=1)),now+timedelta(seconds=1),True)
        self.assertFalse(a['trades']);self.assertIsNotNone(a['position'])

    def test_gap_and_new_day_freeze_open_spread(self):
        for delta in (timedelta(seconds=20),timedelta(days=1)):
            state,a=enter();s.advance(state,rows(NOW+delta),NOW+delta,True)
            self.assertTrue(a['blocked']);self.assertIsNotNone(a['position'])

    def test_pause_cancels_entry_but_allows_exit(self):
        state=s.fresh();a=pending(state);now=NOW+timedelta(seconds=1)
        s.advance(state,rows(now),now,False);self.assertIsNone(a['position'])
        state,a=enter();now=NOW+timedelta(seconds=2);rr=rows(now);rr[0].update(bid=60,ask=61)
        s.advance(state,rr,now,False);self.assertEqual(len(a['trades']),1)
        self.assertLess(a['trades'][0]['pnl'],0)

    def test_duplicate_second_is_idempotent(self):
        state,a=enter();before=copy.deepcopy(state)
        s.advance(state,rows(NOW+timedelta(seconds=1)),NOW+timedelta(seconds=1),True)
        self.assertEqual(state,before)

    def test_reserve_and_daily_risk_block_entries(self):
        for field,value in [('cash',100),('daily_entries',2),('equity',97000)]:
            state=s.fresh();a=pending(state);a[field]=value
            s.advance(state,rows(NOW+timedelta(seconds=1)),NOW+timedelta(seconds=1),True)
            self.assertIsNone(a['position'])

    def test_storage_migration_pins_and_pause_preserve_legacy_money(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'paths',return_value=(Path(d)/'source',Path(d)/'paper')):
            p.control('start')
            with p.database() as db:
                state=json.loads(db.execute('SELECT state FROM sessions').fetchone()[0]);state['agents']['opening_range']['cash']=99123
                db.execute('UPDATE sessions SET state=?',(json.dumps(state),))
            p.stream_tick([],dict(status='Waiting'),now=NOW)
            first=p.dashboard();self.assertEqual(len(first['live']['agents']),11)
            self.assertEqual(first['live']['agents']['opening_range']['cash'],99123)
            self.assertEqual(first['live']['agents']['trend_pullback']['cash'],100000)
            with p.database() as db:
                state=json.loads(db.execute('SELECT state FROM sessions').fetchone()[0]);pending(state['spreads'])
                db.execute('UPDATE sessions SET state=?',(json.dumps(state),))
            self.assertEqual(p.pinned_contracts(),{'L','S'})
            p.control('pause');self.assertEqual(p.pinned_contracts(),set())
            self.assertEqual(len(p.backtest('2026-09-01','2026-09-02')['agents']),2)

class EndToEndTests(unittest.TestCase):
    def test_one_hour_stream_warms_candles_signals_then_fills_next_second(self):
        state=s.fresh();start=NOW-timedelta(hours=1)
        closes=[25000,25005,25010,25015,25020,25025,25030,25035,25040,25045,25030,25080]
        for second in range(3601):
            now=start+timedelta(seconds=second);rr=rows(now)
            for r in rr:r['spot']=closes[min(second//300,11)]
            s.advance(state,rr,now,True)
            if second<3600:
                self.assertTrue(all(not a['position'] and not a['pending'] for a in state['agents'].values()))
        self.assertEqual(len(state['candles']),12)
        self.assertTrue(all(a['pending'] for a in state['agents'].values()))
        now=NOW+timedelta(seconds=1);s.advance(state,rows(now),now,True)
        self.assertTrue(all(a['position'] for a in state['agents'].values()))

    def test_stale_spot_and_expiry_day_block_warmup(self):
        for change in ('spot_at','expiry'):
            state=s.fresh();rr=rows()
            for r in rr:r[change]=(NOW-timedelta(seconds=10)).isoformat() if change=='spot_at' else '2026-09-28'
            s.advance(state,rr,NOW,True)
            self.assertIsNone(state['minute'])
