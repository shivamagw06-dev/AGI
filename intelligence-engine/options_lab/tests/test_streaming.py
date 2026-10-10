import copy
import json
import sqlite3
import tempfile
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from options_lab import paper_agents as paper
from options_lab.streaming import QuoteCache, universe, decode, NIFTY
from options_lab.proto.MarketDataFeed_pb2 import FeedResponse, NORMAL_OPEN

NOW = datetime(2026,9,28,4,30,tzinfo=timezone.utc)
KEY = 'NSE_FO|123'
META = {KEY:dict(instrument_key=KEY,option_type='CE',strike=25000,expiry='2026-10-06',lot_size=65)}


def payload(at=NOW,bid=99,ask=100,size=1000):
    return dict(currentTs=int(at.timestamp()*1000),marketInfo=dict(segmentStatus={'NSE_FO':'NORMAL_OPEN'}),
        feeds={NIFTY:dict(fullFeed=dict(indexFF=dict(ltpc=dict(ltp=25060)))),
               KEY:dict(fullFeed=dict(marketFF=dict(ltpc=dict(ltp=100),vtt=1000,oi=500,
                        marketLevel=dict(bidAskQuote=[dict(bidP=bid,askP=ask,bidQ=size,askQ=size)]))))})


def row(at=NOW,quote_at=None):
    cache=QuoteCache();cache.ingest(payload(quote_at or at),at)
    return cache.rows(at,META)


def seeded():
    state=paper.fresh_state()
    state['day']='2026-09-28';state['last_at']=(NOW-timedelta(seconds=1)).isoformat()
    state['history']=[dict(at=f'2026-09-28T{hour}:00+05:30',minute=minute,spot=25000)
                      for hour,minute in [('09:15',555),('09:30',570),('09:45',585)]]
    return state


class StreamTests(unittest.TestCase):
    def test_real_protobuf_roundtrip_with_market_status(self):
        msg=FeedResponse();msg.currentTs=int(NOW.timestamp()*1000)
        msg.marketInfo.segmentStatus['NSE_FO']=NORMAL_OPEN
        msg.feeds[NIFTY].fullFeed.indexFF.ltpc.ltp=25060
        market=msg.feeds[KEY].fullFeed.marketFF
        market.vtt=1000;market.oi=500
        q=market.marketLevel.bidAskQuote.add();q.bidP=99;q.askP=100;q.bidQ=1000;q.askQ=1000
        cache=QuoteCache();cache.ingest(decode(msg.SerializeToString()),NOW)
        self.assertEqual(cache.rows(NOW,META)[0]['ask'],100)

    def test_no_stale_future_or_closed_market_quotes(self):
        for offset in (-6,1):
            cache=QuoteCache();cache.ingest(payload(NOW+timedelta(seconds=offset)),NOW)
            self.assertEqual(cache.rows(NOW,META),[])
        cache=QuoteCache();cache.ingest(payload(),NOW)
        self.assertFalse(cache.rows(NOW+timedelta(seconds=6),META))
        cache.ingest(dict(marketInfo=dict(segmentStatus={'NSE_FO':'NORMAL_CLOSE'})),NOW)
        self.assertFalse(cache.rows(NOW,META))

    def test_greeks_message_and_duplicate_do_not_freshen_quotes(self):
        cache=QuoteCache();cache.ingest(payload(),NOW)
        later=NOW+timedelta(seconds=6)
        cache.ingest(dict(currentTs=int(later.timestamp()*1000),feeds={KEY:dict(firstLevelWithGreeks=dict())}),later)
        self.assertEqual(cache.values[KEY]['at'],NOW)
        cache.ingest(payload(bid=80,ask=81),NOW+timedelta(seconds=1))
        self.assertEqual(cache.values[KEY]['bid'],99)
        self.assertFalse(cache.rows(later,META))

    def test_per_instrument_age_and_whole_lot_depth(self):
        cache=QuoteCache();cache.ingest(payload(size=64),NOW)
        self.assertFalse(cache.rows(NOW,META))
        cache=QuoteCache();cache.ingest(payload(),NOW)
        later=NOW+timedelta(seconds=6)
        p=payload(later);p['feeds'].pop(KEY);cache.ingest(p,later)
        self.assertFalse(cache.rows(later,META))

    def test_one_second_entry_and_exit_without_indicator_acceleration(self):
        state=seeded();paper.step(state,row(),wall_now=NOW,interval_seconds=1)
        a=state['agents']['opening_range'];self.assertIsNotNone(a['pending'])
        second=NOW+timedelta(seconds=1)
        paper.step(state,row(second),wall_now=second,interval_seconds=1)
        self.assertIsNotNone(a['position'])
        third=NOW+timedelta(seconds=2)
        cache=QuoteCache();cache.ingest(payload(third,bid=70,ask=71),third)
        paper.step(state,cache.rows(third,META),wall_now=third,interval_seconds=1)
        self.assertEqual(len(a['trades']),1)
        self.assertEqual(len(state['history']),4)
        self.assertGreater(a['max_drawdown'],0)

    def test_same_quote_cannot_fill_next_second(self):
        state=seeded();paper.step(state,row(),wall_now=NOW,interval_seconds=1)
        second=NOW+timedelta(seconds=1)
        paper.step(state,row(second,quote_at=NOW),wall_now=second,interval_seconds=1)
        self.assertIsNone(state['agents']['opening_range']['position'])

    def test_mid_window_start_cannot_invent_opening_sample(self):
        state=paper.fresh_state();mid=NOW-timedelta(minutes=10)
        paper.step(state,row(mid),wall_now=mid,interval_seconds=1)
        self.assertFalse(state['history'])

    def test_duplicate_second_is_idempotent(self):
        state=seeded();paper.step(state,row(),wall_now=NOW,interval_seconds=1)
        before=copy.deepcopy(state)
        at=NOW+timedelta(milliseconds=500)
        paper.step(state,row(at),wall_now=at,interval_seconds=1)
        self.assertEqual(before,state)

    def test_universe_caps_window_and_keeps_open_position(self):
        contracts=[dict(instrument_key=f'NSE_FO|{s}{side}',instrument_type=side,
                        strike_price=s,lot_size=65,expiry='2026-10-06')
                   for s in range(23000,27000,50) for side in ['CE','PE']]
        pinned=contracts[0]['instrument_key']
        selected=universe(contracts,25000,NOW,{pinned})
        self.assertEqual(len(selected),43);self.assertIn(pinned,selected)
        self.assertTrue(all(abs(m['strike']-25000)<=500 for k,m in selected.items() if k!=pinned))

    def test_stream_state_persistence_gap_and_pause(self):
        with tempfile.TemporaryDirectory() as d,patch('options_lab.paper_agents.paths',return_value=(Path(d)/'source',Path(d)/'paper.sqlite')):
            paper.control('start')
            paper.stream_tick([],dict(status='Waiting for market'),now=NOW)
            self.assertEqual(paper.dashboard()['live']['version'],'nifty-paper-v2-1s')
            state=seeded();state['version']='nifty-paper-v2-1s'
            with paper.database() as db:
                db.execute('UPDATE sessions SET state=? WHERE id=1',(json.dumps(state),))
            paper.stream_tick(row(),dict(status='Streaming'),now=NOW)
            second=NOW+timedelta(seconds=1)
            paper.stream_tick(row(second),dict(status='Streaming'),now=second)
            self.assertIsNotNone(paper.dashboard()['live']['agents']['opening_range']['position'])
            paper.control('pause')
            third=NOW+timedelta(seconds=2)
            paper.stream_tick([],dict(status='Disconnected'),now=third)
            a=paper.dashboard()['live']['agents']['opening_range']
            self.assertTrue(a['blocked']);self.assertFalse(a['trades']);self.assertIsNotNone(a['position'])
            with paper.database() as db:
                frames=db.execute('SELECT payload FROM second_frames').fetchall()
                self.assertEqual(len(frames),2)
                self.assertEqual(json.loads(zlib.decompress(frames[0][0]))[0]['quote_at'],NOW.isoformat())

    def test_upgrade_does_not_reset_existing_capital_or_positions(self):
        with tempfile.TemporaryDirectory() as d,patch('options_lab.paper_agents.paths',return_value=(Path(d)/'source',Path(d)/'paper.sqlite')):
            paper.control('start');state=paper.fresh_state()
            state['agents']['opening_range'].update(cash=93000,position=dict(instrument_key=KEY))
            with paper.database() as db:
                db.execute('UPDATE sessions SET state=? WHERE id=1',(json.dumps(state),))
            paper.stream_tick([],dict(status='Waiting'),now=NOW)
            a=paper.dashboard()['live']['agents']['opening_range']
            self.assertEqual(a['cash'],93000);self.assertTrue(a['blocked']);self.assertIsNotNone(a['position'])

    def test_slow_collector_cannot_write_live_state_in_stream_mode(self):
        with patch.dict('os.environ',{'NIFTY_PAPER_STREAM_ENABLED':'true'}),patch.object(paper,'database') as db:
            paper.tick();db.assert_not_called()

if __name__=='__main__':unittest.main()

class StreamWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_documented_direct_handshake_only_on_auth_endpoint_rejection(self):
        from options_lab.streaming import handshake
        from urllib.error import HTTPError
        with patch('options_lab.streaming.authorize',return_value='wss://feed.upstox.com/?code=one-time'):
            uri,headers,mode=await handshake('secret')
            self.assertNotIn('Authorization',headers)
            self.assertEqual(mode,'authorized URL')
        for status in (401,403):
            with patch('options_lab.streaming.authorize',side_effect=HTTPError('https://api.upstox.com',status,'denied',{},None)):
                uri,headers,mode=await handshake('secret')
                self.assertEqual(uri,'wss://api.upstox.com/v3/feed/market-data-feed')
                self.assertEqual(headers['Authorization'],'Bearer secret')
                self.assertEqual(mode,'direct feed')
        with patch('options_lab.streaming.authorize',side_effect=HTTPError('https://api.upstox.com',429,'limit',{},None)):
            with self.assertRaises(HTTPError): await handshake('secret')

    async def test_socket_auth_rejection_is_reported_without_credentials(self):
        from unittest.mock import AsyncMock
        from types import SimpleNamespace
        from options_lab.streaming import StreamWorker
        w=StreamWorker();error=ValueError('wss://secret/?token=private')
        error.response=SimpleNamespace(status_code=403)
        w.session=AsyncMock(side_effect=error)
        async def persist(*args,**kwargs): w.stop.set()
        w.persist=AsyncMock(side_effect=persist)
        with patch('builtins.print'):
            await w.run()
        self.assertEqual(w.status['authorization'],'Rejected')
        self.assertIn('feed permissions',w.status['error'])
        self.assertNotIn('private',json.dumps(w.status))

    async def test_closed_market_auth_checks_subscription_then_idles(self):
        from unittest.mock import AsyncMock, MagicMock
        from options_lab.streaming import StreamWorker
        import asyncio
        class Socket:
            def __init__(self): self.sent=[]
            async def send(self,message): self.sent.append(json.loads(message))
            def __aiter__(self): return self
            async def __anext__(self): await asyncio.Future()
        class Connection:
            async def __aenter__(self): return ws
            async def __aexit__(self,*args): pass
        ws=Socket();w=StreamWorker()
        async def reader(_):
            w.cache.messages=1
            await asyncio.Future()
        w.reader=reader
        async def persist(*args,**kwargs): await asyncio.sleep(0)
        w.persist=AsyncMock(side_effect=persist)
        contracts=[dict(instrument_key=KEY,instrument_type='CE',strike_price=25000,lot_size=65,expiry='2026-10-06')]
        with patch('options_lab.streaming.discover',return_value=(contracts,25000)),patch('options_lab.streaming.universe',return_value=META),patch('options_lab.streaming.authorize',return_value='wss://feed.example.invalid'),patch('options_lab.streaming.load_access_token',return_value='test'),patch('options_lab.streaming.paper.pinned_contracts',return_value=set()),patch('options_lab.streaming._is_market_session',return_value=False),patch('websockets.asyncio.client.connect',return_value=Connection()):
            await w.session()
        self.assertEqual(w.status['authorization'],'Verified')
        self.assertFalse(w.status['connected'])
        self.assertEqual(set(ws.sent[0]['data']['instrumentKeys']),{NIFTY,KEY})
        self.assertEqual(ws.sent[0]['data']['mode'],'full')
        self.assertEqual(w.status['status'],'Waiting for market')

    async def test_reconnect_error_never_leaks_token_or_url(self):
        from unittest.mock import AsyncMock
        from options_lab.streaming import StreamWorker
        w=StreamWorker()
        w.session=AsyncMock(side_effect=ValueError('wss://secret.example/?token=never-log-me'))
        async def persist(*args,**kwargs): w.stop.set()
        w.persist=AsyncMock(side_effect=persist)
        with patch('builtins.print') as output:
            await w.run()
        self.assertNotIn('never-log-me',str(output.call_args_list))
        self.assertNotIn('never-log-me',json.dumps(w.status))
