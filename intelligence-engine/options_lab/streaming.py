"""One shared Upstox V3 read-only stream, one-second paper evaluation.

No order endpoints or trading SDK. REST is only used for contract discovery and
WebSocket authorization. Timestamps and market status gate every simulated fill.
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import resource
import signal
import sys
import time
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone

from . import paper_agents as paper
from .automation import _is_market_session
from .upstox_live import UpstoxClient, UpstoxLiveError, load_access_token, DEFAULT_UNDERLYING_KEY as NIFTY

MAX_AGE = 5
MAX_CONTRACTS = 42


def decode(data):
    from google.protobuf.json_format import MessageToDict
    from .proto.MarketDataFeed_pb2 import FeedResponse
    message = FeedResponse()
    message.ParseFromString(data)
    return MessageToDict(message, preserving_proto_field_name=True)


def authorize(token):
    request = urllib.request.Request(
        'https://api.upstox.com/v3/feed/market-data-feed/authorize',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    uri = result.get('data', {}).get('authorized_redirect_uri', '')
    if result.get('status') != 'success' or not uri.startswith('wss://'):
        raise ValueError('Market feed authorization unavailable')
    return uri  # Never logged or persisted: it contains a short-lived credential.


async def handshake(token):
    try:
        return await asyncio.to_thread(authorize,token), {'Accept':'*/*'}, 'authorized URL'
    except urllib.error.HTTPError as error:
        if error.code not in (401,403):
            raise
        # Upstox also documents direct Bearer authentication on this endpoint.
        # This is the same read-only feed, never a trading API or weaker TLS.
        return ('wss://api.upstox.com/v3/feed/market-data-feed',
                {'Accept':'*/*','Authorization':f'Bearer {token}'}, 'direct feed')


def discover(now):
    client = UpstoxClient(load_access_token(), timeout_seconds=15)
    contracts = client.option_contracts(NIFTY)
    eligible = [c for c in contracts if c.get('instrument_type') in ('CE', 'PE')
                and c.get('expiry') and c.get('instrument_key') and c.get('strike_price')
                and 2 <= (datetime.fromisoformat(c['expiry']).date()-now.astimezone(paper.IST).date()).days <= 14]
    if not eligible:
        raise ValueError('No eligible NIFTY contracts')
    expiry = min(c['expiry'] for c in eligible)
    chain = client.option_chain(NIFTY, expiry)
    spots = [paper.number(c.get('underlying_spot_price')) for c in chain]
    spot = next((s for s in spots if s and s > 0), None)
    if spot is None:
        raise ValueError('No reference spot for contract discovery')
    return contracts, spot


def universe(contracts, spot, now, pinned=()):
    today = now.astimezone(paper.IST).date()
    eligible = [c for c in contracts if c.get('instrument_type') in ('CE','PE')
                and c.get('expiry') and c.get('instrument_key') and paper.number(c.get('strike_price'))
                and paper.number(c.get('lot_size')) and float(c['lot_size']).is_integer()
                and float(c['lot_size']) > 0
                and 2 <= (datetime.fromisoformat(c['expiry']).date()-today).days <= 14]
    expiry = min((c['expiry'] for c in eligible), default=None)
    nearest = sorted((c for c in eligible if c['expiry']==expiry),
                     key=lambda c:(abs(float(c['strike_price'])-spot),float(c['strike_price']),c['instrument_type']))[:MAX_CONTRACTS]
    chosen = {c['instrument_key']: c for c in nearest}
    # Never unsubscribe an open or pending contract when the ATM window moves.
    chosen.update({c['instrument_key']:c for c in contracts if c.get('instrument_key') in pinned})
    return {key:dict(instrument_key=key, option_type=c['instrument_type'],
                     strike=float(c['strike_price']),expiry=c['expiry'],lot_size=int(c['lot_size']))
            for key,c in chosen.items()}


class QuoteCache:
    def __init__(self):
        self.values = {}
        self.market_open = False
        self.messages = 0
        self.last_message_at = None

    def ingest(self, payload, received):
        self.messages += 1
        self.last_message_at = received.isoformat()
        segments = payload.get('marketInfo', {}).get('segmentStatus', {})
        if 'NSE_FO' in segments:
            self.market_open = segments['NSE_FO'] in ('NORMAL_OPEN', 2)
        ts = paper.number(payload.get('currentTs'))
        if ts is None:
            return
        at = datetime.fromtimestamp(ts/1000, timezone.utc)
        if not 0 <= (received-at).total_seconds() <= MAX_AGE:
            return
        for key, feed in payload.get('feeds', {}).items():
            full = feed.get('fullFeed', {})
            body = full.get('indexFF') if key == NIFTY else full.get('marketFF')
            if not body:
                continue  # Do not refresh a quote timestamp using Greeks-only messages.
            previous = self.values.get(key)
            if previous and at <= previous['at']:
                continue
            if key == NIFTY:
                spot = paper.number(body.get('ltpc', {}).get('ltp'))
                if spot and spot > 0:
                    self.values[key] = dict(at=at,spot=spot)
            else:
                levels = body.get('marketLevel', {}).get('bidAskQuote', [])
                if not levels:
                    self.values.pop(key,None)
                    continue
                q = levels[0]
                self.values[key] = dict(at=at,bid=q.get('bidP'),ask=q.get('askP'),
                    bid_size=q.get('bidQ'),ask_size=q.get('askQ'),volume=body.get('vtt'),oi=body.get('oi'),
                    ltp=body.get('ltpc',{}).get('ltp'),iv=body.get('iv'),greeks=body.get('optionGreeks',{}))

    def rows(self, now, metadata):
        spot = self.values.get(NIFTY)
        if not self.market_open or not spot or not 0 <= (now-spot['at']).total_seconds() <= MAX_AGE:
            return []
        rows = []
        for key, meta in metadata.items():
            quote = self.values.get(key)
            if not quote or not 0 <= (now-quote['at']).total_seconds() <= MAX_AGE:
                continue
            # The simulated whole lot must fit the displayed best bid and ask.
            if (paper.number(quote.get('bid_size')) or 0) < meta['lot_size'] or (paper.number(quote.get('ask_size')) or 0) < meta['lot_size']:
                continue
            rows.append(dict(**meta,captured_at=now.isoformat(),quote_at=quote['at'].isoformat(),
                             spot_at=spot['at'].isoformat(),spot=spot['spot'],provider='upstox',
                             underlying_key=NIFTY,**{k:v for k,v in quote.items() if k != 'at'}))
        return rows


class StreamWorker:
    def __init__(self):
        self.stop = asyncio.Event()
        self.cache = QuoteCache()
        self.metadata = {}
        self.status = dict(status='Starting stream', interval_seconds=1, connected=False,
                           source='Upstox V3 WebSocket', messages=0, evaluations=0, recorded_frames=0,
                           retention_days=14, started_at=datetime.now(timezone.utc).isoformat())
        self.cpu_at = time.process_time()
        self.wall_at = time.monotonic()
        self.pruned_day = None

    async def persist(self, rows, now):
        start = time.perf_counter()
        self.status.update(heartbeat_at=now.isoformat(),messages=self.cache.messages,
                           subscribed_contracts=len(self.metadata),fresh_contracts=len(rows),
                           last_message_at=self.cache.last_message_at)
        if rows:
            self.status['evaluations'] += 1
            self.status['recorded_frames'] += 1
            self.status['last_evaluation_at'] = now.isoformat()
        elapsed = time.monotonic()-self.wall_at
        if elapsed >= 10:
            self.status['cpu_percent_one_core'] = round(100*(time.process_time()-self.cpu_at)/elapsed,2)
            self.status['peak_memory_mb'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024),1)
            self.cpu_at,self.wall_at = time.process_time(),time.monotonic()
        prune = self.pruned_day != now.date()
        await asyncio.to_thread(paper.stream_tick,rows,dict(self.status),now=now,prune=prune)
        self.pruned_day = now.date()
        self.status['processing_ms'] = round((time.perf_counter()-start)*1000,2)

    async def reader(self, ws):
        async for message in ws:
            if not isinstance(message,bytes):
                raise ValueError('Expected binary Upstox feed')
            self.cache.ingest(decode(message), datetime.now(timezone.utc))

    async def subscribe(self, ws, method, keys):
        if keys:
            await ws.send(json.dumps(dict(guid=str(uuid.uuid4()),method=method,
                data=dict(mode='full',instrumentKeys=sorted(keys)))).encode())

    async def session(self):
        from websockets.asyncio.client import connect
        now = datetime.now(timezone.utc)
        contracts,spot = await asyncio.to_thread(discover,now)
        pinned = await asyncio.to_thread(paper.pinned_contracts)
        self.metadata = universe(contracts,spot,now,pinned)
        uri,headers,mode = await handshake(load_access_token())
        self.status['connection_mode'] = mode
        # The URL is authorized by Upstox. TLS certificate verification stays on.
        async with connect(uri,additional_headers=headers,open_timeout=20,ping_interval=20,ping_timeout=20,max_size=4*1024*1024,max_queue=16) as ws:
            self.cache = QuoteCache()
            await self.subscribe(ws,'sub',set(self.metadata)|{NIFTY})
            self.status.update(connected=True,authorization='Verified',error=None)
            reader = asyncio.create_task(self.reader(ws))
            started = refreshed = time.monotonic()
            deadline = time.monotonic()
            try:
                while not self.stop.is_set():
                    if reader.done():
                        await reader
                        raise ConnectionError('Feed closed')
                    now = datetime.now(timezone.utc)
                    in_session = _is_market_session(now)
                    rows = self.cache.rows(now,self.metadata) if in_session else []
                    self.status['status'] = ('Streaming · 1-second paper checks' if rows else
                        'Waiting for market' if not in_session else 'Waiting for fresh quotes / market open')
                    await self.persist(rows,now)
                    # Startup verifies authentication even after hours, then closes.
                    if not in_session and (self.cache.messages or time.monotonic()-started>=15):
                        break
                    if in_session and time.monotonic()-refreshed>=300:
                        spot_quote = self.cache.values.get(NIFTY)
                        if spot_quote:
                            pinned = await asyncio.to_thread(paper.pinned_contracts)
                            updated = universe(contracts,spot_quote['spot'],now,pinned)
                            await self.subscribe(ws,'sub',set(updated)-set(self.metadata))
                            await self.subscribe(ws,'unsub',set(self.metadata)-set(updated))
                            self.metadata = updated
                            self.cache.values = {k:v for k,v in self.cache.values.items() if k==NIFTY or k in updated}
                        refreshed = time.monotonic()
                    if in_session and self.cache.last_message_at and (now-paper.timestamp(self.cache.last_message_at)).total_seconds()>20:
                        raise ConnectionError('Feed stalled')
                    if in_session and not self.cache.last_message_at and time.monotonic()-started>20:
                        raise ConnectionError('No feed messages')
                    deadline += 1
                    if deadline < time.monotonic():
                        deadline = time.monotonic()+1  # Never burst to catch up missed seconds.
                    self.status['loop_lag_ms'] = round(max(0,time.monotonic()-(deadline-1))*1000,2)
                    try:
                        await asyncio.wait_for(self.stop.wait(),timeout=max(.001,deadline-time.monotonic()))
                    except asyncio.TimeoutError:
                        pass
            finally:
                reader.cancel()
                await asyncio.gather(reader,return_exceptions=True)
                self.status['connected'] = False

    async def run(self):
        delay = 2
        checked = False
        while not self.stop.is_set():
            now = datetime.now(timezone.utc)
            if checked and not _is_market_session(now):
                self.status.update(status='Waiting for market',connected=False)
                await self.persist([],now)
                wait = 15
            else:
                try:
                    await self.session()
                    checked = True
                    delay = 2
                    wait = 1
                except Exception as error:
                    # Exception strings can contain the authorized WSS URI/token.
                    code = getattr(error,'code',None) or getattr(getattr(error,'response',None),'status_code',None)
                    auth_error = code in (401,403) or (isinstance(error,UpstoxLiveError) and 'authorization failed' in str(error))
                    reason = 'Upstox streaming access rejected; check token validity and feed permissions' if auth_error else f'Stream reconnecting ({type(error).__name__})'
                    if auth_error:
                        self.status['authorization'] = 'Rejected'
                    self.status.update(status=reason,error=reason,connected=False)
                    print(json.dumps(dict(event='paper_stream_retry',reason=reason)),flush=True)
                    await self.persist([],datetime.now(timezone.utc))
                    wait,delay = delay,min(60,delay*2)
            until = time.monotonic()+wait
            while not self.stop.is_set() and time.monotonic()<until:
                try:
                    await asyncio.wait_for(self.stop.wait(),timeout=min(15,until-time.monotonic()))
                except asyncio.TimeoutError:
                    await self.persist([],datetime.now(timezone.utc))
        self.status.update(status='Stream stopped',connected=False)
        await self.persist([],datetime.now(timezone.utc))


def main():
    # One worker per durable account database, including during deployment overlap.
    _,path = paper.paths()
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.stream.lock').open('w') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('A paper stream worker is already active')
        async def run():
            worker = StreamWorker()
            loop = asyncio.get_running_loop()
            for signum in (signal.SIGINT,signal.SIGTERM):
                loop.add_signal_handler(signum,worker.stop.set)
            await worker.run()
        asyncio.run(run())


if __name__ == '__main__':
    main()
