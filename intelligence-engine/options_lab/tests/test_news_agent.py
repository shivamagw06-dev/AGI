import copy
import json
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from options_lab import news_agent as n, news_monitor as m, paper_agents as p

START=datetime.fromisoformat('2026-09-29T10:00:00+05:30')
CAL=dict(date='2026-09-29',windows=[])
KEY='NSE_EQ|INE002A01018'

def article(at=None,**kwargs):
    at=at or START+timedelta(seconds=150)
    return dict(id='event1',heading='RBI announces repo rate cut',url='https://upstox.com/news/test/',
                first_seen_at=at.isoformat(),published_at=(at-timedelta(seconds=5)).isoformat(),
                original_published_at=(at-timedelta(seconds=5)).isoformat(),live_discovery=True,revised=False,**kwargs)

def snapshot(now,articles=None):return dict(available=True,last_success_at=now.isoformat(),articles=articles or [])

def rows(now,spot=22520,bid=49,ask=50):
    return [dict(instrument_key='NSE_FO|CALL',option_type='CE',strike=22500,expiry='2026-10-06',
                 provider='upstox',underlying_key='NSE_INDEX|Nifty 50',lot_size=65,
                 bid=bid,ask=ask,bid_size=650,ask_size=650,oi=10000,volume=10000,
                 captured_at=now.isoformat(),quote_at=now.isoformat(),spot_at=now.isoformat(),spot=spot)]

def prepared(news=True):
    state=n.fresh(START-timedelta(seconds=1))
    for sec in range(241):
        now=START+timedelta(seconds=sec)
        articles=[article()] if news and sec>=150 else []
        n.advance(state,rows(now,22500 if sec<180 else 22520),snapshot(now,articles),now,True,CAL)
    return state

def tick(state,sec,news=True,**kw):
    now=START+timedelta(seconds=sec)
    n.advance(state,rows(now,**kw),snapshot(now,[article()] if news else []),now,True,CAL)

class NewsAgentTests(unittest.TestCase):
    def test_macro_topics_exclude_recap_prediction_and_company_events(self):
        for title in ('RBI cuts repo rate by 25 bps','India CPI inflation falls to 3%','Fed holds interest rates steady','OPEC announces oil production cut'):
            self.assertIsNotNone(n.topic(title),title)
        for title in ('RBI may cut repo rate','RBI expected to cut rates','RBI cuts rates?','Yesterday RBI cuts repo rate','HCL buys AI business','Market crash recap','Burry warns Fed may hike rates','Dr Reddy rises after tariff exemption'):
            self.assertIsNone(n.topic(title),title)

    def test_first_batch_and_pre_activation_articles_never_arm(self):
        for change in ({'live_discovery':False},{'first_seen_at':START.isoformat()},{'revised':True},
                       {'published_at':(START-timedelta(hours=1)).isoformat(),'original_published_at':(START-timedelta(hours=1)).isoformat()}):
            now=START+timedelta(minutes=3);state=n.fresh(START)
            a=article();a.update(change)
            n.ingest(state,snapshot(now,[a]),now)
            self.assertFalse(state['events'],change)

    def test_future_or_delayed_publication_does_not_arm(self):
        now=START+timedelta(minutes=3)
        for delta in (10,-601):
            state=n.fresh(START);a=article()
            a['original_published_at']=(now+timedelta(seconds=delta)).isoformat()
            n.ingest(state,snapshot(now,[a]),now);self.assertFalse(state['events'])

    def test_duplicate_and_restart_cannot_rearm_event(self):
        now=START+timedelta(minutes=3);state=n.fresh(START)
        n.ingest(state,snapshot(now,[article()]),now)
        self.assertEqual(len(state['events']),1)
        state=json.loads(json.dumps(state));a=article();a['id']='copy'
        n.ingest(state,snapshot(now+timedelta(seconds=1),[a]),now+timedelta(seconds=1))
        self.assertEqual(len(state['events']),1)
        self.assertIn('Duplicate',state['decisions'][-1]['reason'])

    def test_two_independent_accounts_require_next_quote_and_record_evidence(self):
        state=prepared()
        for a in state['agents'].values():self.assertIsNotNone(a['pending']);self.assertIsNone(a['position'])
        tick(state,241)
        for a in state['agents'].values():
            self.assertEqual(a['position']['quantity'],65)
            self.assertLess(a['equity'],100000)
            self.assertEqual(a['daily_entries'],1)
        self.assertEqual(state['agents']['news_reaction']['position']['news']['id'],'event1')
        self.assertIsNone(state['agents']['price_control']['position']['news'])
        self.assertEqual(state['agents']['news_reaction']['cash'],state['agents']['price_control']['cash'])
        tick(state,242,bid=75,ask=76)
        for a in state['agents'].values():
            self.assertEqual(a['trades'][0]['reason'],'Premium target')
            self.assertGreater(a['trades'][0]['entry_cost']+a['trades'][0]['exit_cost'],0)
            self.assertAlmostEqual(a['cash']-100000,a['trades'][0]['pnl'],places=2)

    def test_control_can_trade_without_news(self):
        state=prepared(False);tick(state,241,False)
        self.assertIsNone(state['agents']['news_reaction']['position'])
        self.assertIsNotNone(state['agents']['price_control']['position'])

    def test_confirmation_cannot_predate_receipt(self):
        state=prepared(False);now=START+timedelta(seconds=240)
        n.ingest(state,snapshot(now,[article(now)]),now)
        self.assertIsNone(n.active_event(state,now,int((START+timedelta(seconds=180)).timestamp())))

    def test_same_quote_cannot_fill_next_second(self):
        state=prepared();now=START+timedelta(seconds=241);q=rows(now)
        q[0]['quote_at']=(now-timedelta(seconds=1)).isoformat()
        n.advance(state,q,snapshot(now,[article()]),now,True,CAL)
        self.assertTrue(all(a['position'] is None for a in state['agents'].values()))

    def test_stale_news_cancels_news_pending_only(self):
        state=prepared();now=START+timedelta(seconds=241)
        n.advance(state,rows(now),dict(available=False),now,True,CAL)
        self.assertIsNone(state['agents']['news_reaction']['position'])
        self.assertIsNotNone(state['agents']['price_control']['position'])

    def test_pause_cancels_entry_but_exits_continue(self):
        state=prepared();now=START+timedelta(seconds=241)
        n.advance(state,rows(now),snapshot(now,[article()]),now,False,CAL)
        self.assertTrue(all(a['position'] is None for a in state['agents'].values()))
        state=prepared();tick(state,241);now=START+timedelta(seconds=242)
        n.advance(state,rows(now,bid=35,ask=36),{},now,False,CAL)
        self.assertTrue(all(a['trades'][0]['reason']=='Premium stop' for a in state['agents'].values()))

    def test_gap_keeps_position_then_exits_at_current_quote_and_locks_day(self):
        state=prepared();tick(state,241);now=START+timedelta(seconds=242)
        n.advance(state,[],{},now,True,CAL)
        self.assertTrue(all(a['blocked'] and a['position'] for a in state['agents'].values()))
        tick(state,250,bid=20,ask=20.5)
        for a in state['agents'].values():
            self.assertTrue(a['day_halted']);self.assertIsNone(a['position'])
            self.assertTrue(a['trades'][0]['data_gap'])
            self.assertEqual(a['trades'][0]['exit_legs'][0]['price'],19.9)
            self.assertIn('recovery',a['trades'][0]['reason'])
        self.assertEqual(n.dashboard(state)['agents']['news_reaction']['data_gap_trades'],1)

    def test_budget_depth_expiry_calendar_and_daily_limits(self):
        for constraint in ('budget','depth','expiry','calendar','daily'):
            state=prepared();now=START+timedelta(seconds=241);q=rows(now);cal=CAL
            if constraint=='budget':q[0].update(bid=99,ask=100)
            if constraint=='depth':q[0]['ask_size']=64
            if constraint=='expiry':q[0]['expiry']='2026-09-29'
            if constraint=='calendar':cal={}
            if constraint=='daily':
                for a in state['agents'].values():a['daily_entries']=2
            n.advance(state,q,snapshot(now,[article()]),now,True,cal)
            self.assertTrue(all(a['position'] is None for a in state['agents'].values()),constraint)

    def test_incomplete_minutes_never_form_signal(self):
        state=n.fresh(START)
        for sec in range(241):
            if 100<sec<112:continue
            now=START+timedelta(seconds=sec)
            n.advance(state,rows(now),snapshot(now,[article()] if sec>=150 else []),now,True,CAL)
        self.assertTrue(all(a['pending'] is None for a in state['agents'].values()))

    def test_event_expires_and_changed_article_cancels_pending(self):
        state=prepared();now=START+timedelta(seconds=241);a=article();a['revised']=True
        n.advance(state,rows(now),snapshot(now,[a]),now,True,CAL)
        self.assertIsNone(state['agents']['news_reaction']['position'])
        self.assertIsNone(n.active_event(state,START+timedelta(minutes=20),int(now.timestamp())))

    def test_poll_freezes_original_date_and_bootstrap_status(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'UPSTOX_ACCESS_TOKEN':'test'}):
            with patch.object(p,'paths',return_value=(Path(tmp)/'source',Path(tmp)/'paper.sqlite3')):
                obj=dict(heading='RBI cuts repo rate',article_link='https://upstox.com/news/test/',published_time=START.timestamp()*1000)
                def get(*args):return dict(status='success',data={KEY:[obj]},metadata={'page':{'page_number':1,'total_pages':1}})
                first=m.poll({KEY:'RELIANCE'},'test',now=START,get=get)
                self.assertFalse(first['articles'][0]['live_discovery'])
                obj['published_time']=(START+timedelta(seconds=60)).timestamp()*1000
                second=m.poll({KEY:'RELIANCE'},'test',now=START+timedelta(seconds=60),get=get)
                self.assertEqual(second['articles'][0]['original_published_at'],START.astimezone(n.p.timestamp(first['articles'][0]['original_published_at']).tzinfo).isoformat())
                self.assertTrue(second['articles'][0]['revised'])
                obj['article_link']='https://upstox.com/news/new/'
                third=m.poll({KEY:'RELIANCE'},'test',now=START+timedelta(seconds=120),get=get)
                self.assertTrue(third['articles'][0]['live_discovery'])

    def test_breakout_reversal_cancels_next_quote_entry(self):
        state=prepared();tick(state,241,spot=22500)
        self.assertTrue(all(a['position'] is None for a in state['agents'].values()))

    def test_downside_breakout_buys_put_without_bearish_text(self):
        state=n.fresh(START-timedelta(seconds=1))
        for sec in range(242):
            now=START+timedelta(seconds=sec)
            q=rows(now,22500 if sec<180 else 22480)
            q[0].update(instrument_key='NSE_FO|PUT',option_type='PE')
            n.advance(state,q,snapshot(now,[article()] if sec>=150 else []),now,True,CAL)
        for a in state['agents'].values():
            self.assertEqual(a['position']['legs'][0]['option_type'],'PE')

    def test_news_exception_preserves_other_agents_and_recovers_open_position(self):
        state=prepared();tick(state,241)
        parent=dict(news_agent=state,research=dict(calendar=CAL),agents={'legacy':{'cash':100123}})
        before=copy.deepcopy(parent['agents'])
        now=START+timedelta(seconds=242)
        bad=article();bad.update(id='bad',original_published_at='malformed')
        with patch.object(n,'advance',side_effect=ValueError('Malformed record')):
            n.isolated_tick(parent,rows(now),snapshot(now,[bad]),now,True)
        self.assertEqual(parent['agents'],before)
        for a in parent['news_agent']['agents'].values():
            self.assertTrue(a['blocked']);self.assertTrue(a['day_halted'])
        now+=timedelta(seconds=1)
        n.isolated_tick(parent,rows(now),snapshot(now),now,True)
        self.assertTrue(all(a['trades'][-1]['data_gap'] for a in parent['news_agent']['agents'].values()))

    def test_time_exit_does_not_depend_on_more_news(self):
        state=prepared();tick(state,241)
        for sec in range(242,1442):tick(state,sec,False)
        for a in state['agents'].values():
            self.assertIsNone(a['position'])
            self.assertEqual(a['trades'][-1]['reason'],'20-minute time exit')

    def test_corrupt_news_snapshot_returns_unavailable_without_interrupting_stream(self):
        import sqlite3
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE paper_news_status(id INTEGER,payload TEXT)')
            db.execute("INSERT INTO paper_news_status VALUES(1,'broken')")
            self.assertEqual(n.snapshot_from_db(db),{})

    def test_stream_persistence_pinning_pause_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(p,'paths',return_value=(Path(tmp)/'source',Path(tmp)/'paper.sqlite3')):
            state=p.fresh_state();state['news_agent']=prepared()
            with p.database() as db:
                db.execute('INSERT INTO sessions VALUES(1,1,?,?)',(START.isoformat(),json.dumps(state)))
            self.assertIn('NSE_FO|CALL',p.pinned_contracts())
            result=p.summary(state)
            self.assertIn('news_agent',result)
            self.assertNotIn('news_reaction',result['agents'])
            p.control('pause')
            with p.database() as db: saved=json.loads(db.execute('SELECT state FROM sessions').fetchone()[0])
            self.assertTrue(all(a['pending'] is None for a in saved['news_agent']['agents'].values()))

if __name__=='__main__':unittest.main()
