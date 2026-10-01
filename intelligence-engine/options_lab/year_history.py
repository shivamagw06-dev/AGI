"""Resumable full-year NIFTY candles; source-specific storage, no synthetic ticks.

Downloads spot first, then eligible expired options within 2,000 spot points
and futures. Provider expiry availability is reported, never inferred complete.
"""
import gzip
import hashlib
from dataclasses import asdict
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from . import data_evidence as e, minute_history as mh, expired_history as h


def db():
    con=sqlite3.connect(e.root()/'year_history.sqlite3',timeout=15)
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript('''CREATE TABLE IF NOT EXISTS chunks(provider TEXT, instrument TEXT, start TEXT, end TEXT,
        asset TEXT, rows INTEGER, first TEXT, last TEXT, sha256 TEXT, PRIMARY KEY(provider,instrument,start,end));
        CREATE TABLE IF NOT EXISTS candles(provider TEXT,instrument TEXT,at TEXT,payload TEXT,
        PRIMARY KEY(provider,instrument,at));
        CREATE TABLE IF NOT EXISTS gaps(provider TEXT,instrument TEXT,start TEXT,end TEXT,reason TEXT,
        PRIMARY KEY(provider,instrument,start,end));''')
    return con


def windows(start,end,days=28):
    cursor=date.fromisoformat(start); end=date.fromisoformat(end)
    while cursor<=end:
        last=min(cursor+timedelta(days=days-1),end)
        yield cursor.isoformat(),last.isoformat()
        cursor=last+timedelta(days=1)


def groww(path,token,**params):
    from .groww_bridge import request
    actions={'/live-data/quote':'quote','/historical/candles':'candles','/historical/expiries':'expiries','/historical/contracts':'contracts'}
    if path not in actions:raise ValueError('Unsupported market-data action')
    return request(actions[path],params)


def normalize(rows):
    import math
    result={}
    for row in rows:
        if not isinstance(row,list) or len(row)<5:raise ValueError('Invalid candle shape')
        t=str(row[0])
        if len(t)==19:t+='+05:30'
        at=datetime.fromisoformat(t)
        if at.tzinfo is None or at.second or at.microsecond:raise ValueError('Invalid candle timestamp')
        o,hi,lo,c=[float(v) for v in row[1:5]]
        if not all(math.isfinite(v) for v in (o,hi,lo,c)) or not 0<lo<=min(o,c)<=max(o,c)<=hi:raise ValueError('Invalid OHLC')
        extras=[float(v) if v is not None else None for v in row[5:7]]
        extras+=(2-len(extras))*[None]
        if any(v is not None and (not math.isfinite(v) or v<0) for v in extras):raise ValueError('Invalid volume/OI')
        key=at.astimezone(mh.p.IST).isoformat();item=[key,o,hi,lo,c,*extras]
        if key in result and result[key]!=item:raise ValueError('Conflicting candles')
        result[key]=item
    return sorted(result.values())


def collect_chunk(provider,key,a,b,asset,token):
    # Groww limits response size. Short windows avoid silently truncated month requests.
    if provider == 'groww' and (date.fromisoformat(b)-date.fromisoformat(a)).days >= 7:
        for first,last in windows(a,b,7):
            collect_safe(provider,key,first,last,asset,token)
        return
    with closing(db()) as con:
        if con.execute('SELECT 1 FROM chunks WHERE provider=? AND instrument=? AND start=? AND end=?',(provider,key,a,b)).fetchone():return
    if e.storage()['free_bytes']<2*1024**3:raise ValueError('Less than 2 GiB free; collection paused')
    if provider=='groww':
        data=groww('/historical/candles',token,exchange='NSE',segment='CASH' if asset=='spot' else 'FNO',groww_symbol=key,
            start_time=a+' 00:00:00',end_time=b+' 23:59:59',candle_interval='1minute')
        raw=data.get('candles',[])
        try:
            rows=normalize(raw)
        except ValueError:
            # Preserve rejected evidence for diagnosis; never manufacture replacement prices.
            target=e.root()/('rejected-'+hashlib.sha256(f'{provider}|{key}|{a}|{b}'.encode()).hexdigest()+'.json.gz')
            with gzip.open(target,'wt') as out:json.dump(raw,out)
            raise
    else:
        mh.download(key,a,b,token,spot=asset=='spot')
        with closing(mh.database()) as con:
            rows=[json.loads(r[0]) for r in con.execute('SELECT payload FROM candles WHERE key=? AND at>=? AND at<? ORDER BY at',(key,a,b+'Z'))]
    if not rows:
        with closing(db()) as con,con:
            con.execute('INSERT OR REPLACE INTO gaps VALUES(?,?,?,?,?)',(provider,key,a,b,'Provider returned no candles'))
        return # Empty remains a coverage gap and is retryable.
    if any(not a<=r[0][:10]<=b for r in rows):raise ValueError('Candles outside requested range')
    with closing(db()) as con,con:
        for row in rows:
            payload=json.dumps(row)
            previous=con.execute('SELECT payload FROM candles WHERE provider=? AND instrument=? AND at=?',(provider,key,row[0])).fetchone()
            if previous and previous[0]!=payload:raise ValueError('Provider corrected cached data; manual reconciliation needed')
            con.execute('INSERT OR IGNORE INTO candles VALUES(?,?,?,?)',(provider,key,row[0],payload))
        con.execute('DELETE FROM gaps WHERE provider=? AND instrument=? AND start=? AND end=?',(provider,key,a,b))
        con.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?)',(provider,key,a,b,asset,len(rows),rows[0][0],rows[-1][0],hashlib.sha256(json.dumps(rows).encode()).hexdigest()))
    time.sleep(.4)


def collect_safe(provider,key,a,b,asset,token):
    try:
        collect_chunk(provider,key,a,b,asset,token)
    except (ValueError, urllib.error.HTTPError) as exc:
        if 'GiB' in str(exc):raise
        if isinstance(exc,urllib.error.HTTPError) and (exc.code in (401,403,429) or exc.code>=500):raise
        # Bad provider chunks must not prevent unrelated contracts from downloading.
        # Only locally generated validation messages and HTTP status are persisted.
        reason=('HTTP '+str(exc.code)) if isinstance(exc,urllib.error.HTTPError) else str(exc)[:180]
        with closing(db()) as con,con:
            con.execute('INSERT OR REPLACE INTO gaps VALUES(?,?,?,?,?)',(provider,key,a,b,reason))
        time.sleep(1)


def summary(provider):
    with closing(db()) as con:
        return {asset:dict(chunks=n,candles=count,first=first,last=last) for asset,n,count,first,last in con.execute(
            "SELECT asset,COUNT(*),SUM(rows),MIN(first),MAX(last) FROM chunks WHERE provider=? AND (provider!='groww' OR julianday(end)-julianday(start)<7) GROUP BY asset",(provider,))}


def run(name,cfg):
    provider=name.split('_')[0]; token=None if provider=='groww' else h.load_access_token()
    a,b=cfg['start'],cfg['end'];state=dict(status='running',start=a,end=b,source=provider,
        download_version='v2',scope='NIFTY spot; expired options within 2,000 points of observed spot opens, final 14 days; expired futures final 28 days. Historical depth unavailable.',
        started_at=datetime.now(timezone.utc).isoformat())
    def update(**kw):
        with closing(db()) as con:
            state['empty_chunks']=con.execute('SELECT COUNT(*) FROM gaps WHERE provider=?',(provider,)).fetchone()[0]
        state.update(kw,heartbeat_at=datetime.now(timezone.utc).isoformat(),coverage=summary(provider));e.write(name,state)
    spot='NSE-NIFTY' if provider=='groww' else h.NIFTY_KEY
    for first,last in windows(a,b,7 if provider=='groww' else 28):
        update(phase='Spot minute candles',through=last);collect_safe(provider,spot,first,last,'spot',token)
    expiries=set()
    if provider=='groww':
        months=sorted({(first[:4],first[5:7]) for first,_ in windows(a,b,1)})
        for year,month in months:
            expiries.update(groww('/historical/expiries',token,exchange='NSE',underlying_symbol='NIFTY',year=int(year),month=int(month)).get('expiries',[]));time.sleep(.4)
    else:expiries.update(h.list_expiries(token=token))
    expiries=sorted(x for x in expiries if a<=x<=b)
    update(returned_expiries=len(expiries),first_returned_expiry=expiries[0] if expiries else None,
        last_returned_expiry=expiries[-1] if expiries else None)
    count=0
    for expiry in expiries:
        first=max(a,(date.fromisoformat(expiry)-timedelta(days=27)).isoformat())
        with closing(db()) as con:
            rows=con.execute('SELECT payload FROM candles WHERE provider=? AND instrument=? AND at>=? AND at<?',(provider,spot,first,expiry+'Z')).fetchall()
        prices=[json.loads(r[0])[1] for r in rows]
        if not prices:continue
        low,high=min(prices)-2000,max(prices)+2000
        if provider=='groww':
            keys=groww('/historical/contracts',token,exchange='NSE',underlying_symbol='NIFTY',expiry_date=expiry).get('contracts',[])
            contracts=[]
            for key in keys:
                if key.endswith('-FUT'):contracts.append((key,'future'))
                elif key.endswith(('-CE','-PE')) and low<=float(key.split('-')[-2])<=high:contracts.append((key,'option'))
        else:
            metadata=[asdict(c) for c in h.list_contracts(expiry,token=token) if c.is_option and low<=c.strike<=high]
            contracts=[(c['instrument_key'],'option') for c in metadata]
            q=urllib.parse.urlencode(dict(instrument_key=h.NIFTY_KEY,expiry_date=expiry))
            futures=h._request(h.API_BASE+'/expired-instruments/future/contract?'+q,token) or []
            contracts += [(c['instrument_key'],'future') for c in futures]
            metadata += [dict(instrument_key=c['instrument_key'],option_type='FUT',strike=0.,expiry=expiry,lot_size=c['lot_size'],underlying_key=h.NIFTY_KEY) for c in futures]
            with closing(mh.database()) as con,con:
                for item in metadata:
                    if int(item.get('lot_size',0))>0:con.execute('INSERT OR REPLACE INTO contracts VALUES(?,?)',(item['instrument_key'],json.dumps(item)))
        for key,asset in contracts:
            begin=max(first,(date.fromisoformat(expiry)-timedelta(days=13)).isoformat()) if asset=='option' else first
            update(phase='Expired '+asset+' minute candles',expiry=expiry,contracts_processed=count)
            collect_safe(provider,key,begin,expiry,asset,token);count+=1
    update(status='download_pass_finished',finished_at=datetime.now(timezone.utc).isoformat(),
        completeness='Provider-returned coverage only. Missing expiry months and empty responses are gaps; not a complete-chain or full-session guarantee.')


if __name__=='__main__':
    try:os.nice(10)
    except (AttributeError,OSError):pass
    name=sys.argv[1]
    try:lock=e.process_lock(name)
    except BlockingIOError:sys.exit(0)
    try:run(name,json.load(sys.stdin))
    except Exception as exc:
        state=e.read(name);state['failure_type']=type(exc).__name__;state['validation_reason']=str(exc)[:180] if isinstance(exc,ValueError) else None;state['http_status']=getattr(exc,'code',None);state.update(status='retry_pending',error='History request or validation failed; cached chunks retained. Check provider entitlement/authentication and disk.',
            retry_after=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat());e.write(name,state)
