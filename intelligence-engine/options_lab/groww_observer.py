"""Official Groww SDK observation stream. Never supplies strategy fills/signals."""
import csv
import gzip
import hashlib
import io
import json
import os
import math
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from . import data_evidence as e, paper_agents as p
from .year_history import groww


def token():
    direct=os.getenv('GROWW_ACCESS_TOKEN','').strip()
    if direct:return direct
    key=os.getenv('GROWW_API_KEY','').strip()
    if key.startswith('eyJ') and len(key)>100:return key
    secret=os.getenv('GROWW_API_SECRET','').strip()
    if not key or not secret:raise ValueError('Groww credentials unavailable')
    now=str(int(time.time()))
    body=json.dumps(dict(key_type='approval',timestamp=now,checksum=hashlib.sha256((secret+now).encode()).hexdigest())).encode()
    req=urllib.request.Request('https://api.groww.in/v1/token/api/access',data=body,
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r:result=json.load(r)
    if not result.get('token'):raise ValueError('Groww token unavailable')
    return result['token']


def timestamp(value):
    try:
        result=float(value)
        if result>1e13:result/=1000
        elif result<1e10:result*=1000
        return result if math.isfinite(result) and result>0 else None
    except (TypeError,ValueError):return None


def leaves(data):
    if not isinstance(data,dict):return
    if 'tsInMillis' in data:
        yield data;return
    for value in data.values():yield from leaves(value)


def select(rows,today,spot):
    candidates=[r for r in rows if r.get('exchange')=='NSE' and r.get('segment')=='FNO' and r.get('underlying_symbol')=='NIFTY' and r.get('expiry_date','')>=today]
    expiries=sorted({r['expiry_date'] for r in candidates if r.get('instrument_type') in ('CE','PE')})
    result=[]
    for row in candidates:
        if not row.get('exchange_token'):continue
        if row.get('instrument_type') in ('CE','PE') and expiries and row['expiry_date']==expiries[0]:
            try:
                if abs(float(row.get('strike_price',0))-spot)<=500:result.append(row)
            except ValueError:pass
    future=sorted((r for r in candidates if r.get('instrument_type')=='FUT'),key=lambda r:r['expiry_date'])
    return result[:42]+future[:1]


def observe():
    from growwapi import GrowwAPI, GrowwFeed
    auth=token();day=datetime.now(p.IST).date().isoformat()
    quote=groww('/live-data/quote',auth,exchange='NSE',segment='CASH',trading_symbol='NIFTY')
    spot=float(quote['last_price'])
    with urllib.request.urlopen('https://growwapi-assets.groww.in/instruments/instrument.csv',timeout=60) as r:
        mapping=select(list(csv.DictReader(io.StringIO(r.read().decode()))),day,spot)
    if not mapping:raise ValueError('No verified NIFTY derivative mapping')
    e.write('groww_mapping',dict(day=day,instruments=mapping))
    feed=GrowwFeed(GrowwAPI(auth)); state=dict(status='subscribing',mode='observation_only',mapped_contracts=len(mapping),messages=0,fresh_messages=0,stale_messages=0,
        started_at=datetime.now(timezone.utc).isoformat(),automatic_failover=False)
    lock=threading.Lock();last={};pending={}
    def callback(kind,getter):
        def receive(_meta):
            data=getter();now=time.time()*1000
            stamps=[timestamp(x.get('tsInMillis')) for x in leaves(data)]
            valid=bool(stamps) and all(t is not None and -1000<=now-t<=5000 for t in stamps)
            with lock:
                state['messages']+=1;state['fresh_messages' if valid else 'stale_messages']+=1
                state['last_received_at']=datetime.now(timezone.utc).isoformat()
                state['last_exchange_at']=datetime.fromtimestamp(max(t for t in stamps if t)/1000,timezone.utc).isoformat() if any(stamps) else None
                # Save changed provider payloads at most once per second, not fabricated ticks.
                payload=json.dumps(data,sort_keys=True)
                if last.get(kind)!=payload:
                    last[kind]=payload;pending[kind]=dict(kind=kind,received_at=state['last_received_at'],fresh=valid,data=data)
        return receive
    derivatives=[dict(exchange='NSE',segment='FNO',exchange_token=r['exchange_token']) for r in mapping]
    feed.subscribe_index_value([dict(exchange='NSE',segment='CASH',exchange_token='NIFTY')],on_data_received=callback('index',feed.get_index_value))
    feed.subscribe_ltp(derivatives,on_data_received=callback('ltp',feed.get_ltp))
    feed.subscribe_market_depth(derivatives,on_data_received=callback('depth',feed.get_market_depth))
    thread=threading.Thread(target=feed.consume,daemon=True);thread.start()
    started=time.monotonic()
    while thread.is_alive() and datetime.now(p.IST).date().isoformat()==day and (datetime.now(p.IST).hour,datetime.now(p.IST).minute)<=(15,40) and time.monotonic()-started<6*3600:
        now=datetime.now(timezone.utc)
        with lock:
            batch=list(pending.values());pending.clear()
            state.update(status='observing' if batch else 'waiting_for_updates',heartbeat_at=now.isoformat())
            if e.storage()['free_bytes']<2*1024**3:raise ValueError('Storage reserve reached')
            if batch:
                with gzip.open(e.root()/f'groww-{day}.jsonl.gz','at') as out:
                    for item in batch:out.write(json.dumps(item)+'\n')
            e.write('groww_stream',state)
        time.sleep(1)
    # Parent supervisor renews mapping/auth at next start. No stale success status.
    state['status']='reconnect_pending';e.write('groww_stream',state)
    from .evidence_archive import digest, durable
    path=e.root()/f'groww-{day}.jsonl.gz'
    if path.exists():
        durable(path)
        e.write(f'groww-{day}-manifest',dict(sha256=digest(path),bytes=path.stat().st_size,mode='sampled_observation'))


if __name__=='__main__':
    try:lock=e.process_lock('groww_stream')
    except BlockingIOError:sys.exit(0)
    try:
        now=datetime.now(p.IST)
        if now.weekday()<5 and (9,0)<=(now.hour,now.minute)<=(15,40):observe()
        else:e.write('groww_stream',dict(status='outside_market_hours',mode='observation_only',heartbeat_at=now.isoformat(),automatic_failover=False))
    except Exception:
        state=e.read('groww_stream');state.update(status='retry_pending',error='Groww stream/auth/mapping unavailable; no automatic failover.',
            retry_after=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat());e.write('groww_stream',state)

    finally:
        # SDK owns non-daemon networking threads; this isolated child renews daily.
        os._exit(0)
