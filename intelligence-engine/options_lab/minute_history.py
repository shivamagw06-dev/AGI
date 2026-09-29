"""Bounded, cached official Upstox one-minute downloads; never writes live frames."""
import hashlib
import json
import sqlite3
import time
import urllib.parse
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from dataclasses import asdict
from . import paper_agents as p, expired_history as h


def database():
    path=p.paths()[1].parent/'nifty_minute_history.sqlite3'
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10);db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''CREATE TABLE IF NOT EXISTS candles(key TEXT,at TEXT,payload TEXT,PRIMARY KEY(key,at));
      CREATE INDEX IF NOT EXISTS candles_at ON candles(at);
      CREATE TABLE IF NOT EXISTS downloads(id TEXT PRIMARY KEY,at TEXT,rows INTEGER,sha256 TEXT);
      CREATE TABLE IF NOT EXISTS contracts(key TEXT PRIMARY KEY,payload TEXT);
      CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,at TEXT,updated TEXT,status TEXT,config TEXT,progress TEXT,result TEXT,error TEXT);''')
    return db


def clean(rows):
    result={}
    for row in rows:
        if not isinstance(row,list) or len(row)<6:raise ValueError('Invalid candle response')
        t=p.timestamp(row[0]).astimezone(p.IST)
        if t.second or t.microsecond:raise ValueError('Expected minute-aligned timestamps')
        values=[p.number(x) for x in row[1:7]]
        if len(values)<6:values.append(0.)
        o,hi,lo,c,v,oi=values
        if any(x is None for x in values) or not 0<lo<=min(o,c)<=max(o,c)<=hi or min(v,oi)<0:
            raise ValueError('Invalid historical OHLC, volume or OI')
        at=t.isoformat();item=[at,*values]
        if at in result and result[at]!=item:raise ValueError('Conflicting historical candles')
        result[at]=item
    return sorted(result.values())


def download(key,start,end,token,*,spot=False):
    cache_id=f'{key}|{start}|{end}|1minute-v1'
    with closing(database()) as db:
        if db.execute('SELECT 1 FROM downloads WHERE id=?',(cache_id,)).fetchone():return
    if spot:
        url='https://api.upstox.com/v3/historical-candle/'+urllib.parse.quote(key,safe='')+'/minutes/1/'+end+'/'+start
        rows=(h._request(url,token) or {}).get('candles',[])
    else:rows=h.candles(key,start,end,interval='1minute',token=token)
    rows=clean(rows)
    if any(not start<=r[0][:10]<=end for r in rows):raise ValueError('Provider returned candles outside requested dates')
    with closing(database()) as db,db:
        for row in rows:
            old=db.execute('SELECT payload FROM candles WHERE key=? AND at=?',(key,row[0])).fetchone()
            payload=json.dumps(row)
            if old and old[0]!=payload:raise ValueError('Cached candle differs from provider; source correction needs review')
            db.execute('INSERT OR IGNORE INTO candles VALUES(?,?,?)',(key,row[0],payload))
        # Empty responses are retriable, never permanently cached as complete.
        if rows:db.execute('INSERT OR REPLACE INTO downloads VALUES(?,?,?,?)',
            (cache_id,datetime.now(timezone.utc).isoformat(),len(rows),hashlib.sha256(json.dumps(rows).encode()).hexdigest()))
    time.sleep(.12)


def spot_rows(start,end):
    with closing(database()) as db:
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM candles WHERE key=? AND at>=? AND at<? ORDER BY at',
                                                    (h.NIFTY_KEY,start,end+'Z'))]


def collect(config,update):
    token=h.load_access_token()
    start=(date.fromisoformat(config['start'])-timedelta(days=45)).isoformat();end=config['end']
    cursor=date.fromisoformat(start)
    while cursor<=date.fromisoformat(end):
        last=min(cursor+timedelta(days=27),date.fromisoformat(end))
        update(phase='Downloading NIFTY one-minute spot candles',through=last.isoformat())
        download(h.NIFTY_KEY,cursor.isoformat(),last.isoformat(),token,spot=True)
        cursor=last+timedelta(days=1)
    spot=spot_rows(start,end)
    if not spot:raise ValueError('No NIFTY minute history returned for this range')
    expiries=h.list_expiries(token=token);count=0;contracts=[]
    for expiry in expiries:
        if not start<=expiry<=(date.fromisoformat(end)+timedelta(days=35)).isoformat() or expiry>=datetime.now(p.IST).date().isoformat():continue
        a=max(start,(date.fromisoformat(expiry)-timedelta(days=35)).isoformat());b=min(end,(date.fromisoformat(expiry)-timedelta(days=2)).isoformat())
        if a>b:continue
        options=[asdict(x) for x in h.list_contracts(expiry,token=token) if x.is_option]
        query=urllib.parse.urlencode(dict(instrument_key=h.NIFTY_KEY,expiry_date=expiry))
        futures=h._request(f'{h.API_BASE}/expired-instruments/future/contract?{query}',token) or []
        fs=[dict(instrument_key=x['instrument_key'],option_type='FUT',strike=0.,expiry=expiry,lot_size=x['lot_size'],underlying_key=h.NIFTY_KEY) for x in futures]
        # Include a broad universe around every observed spot open. This is a
        # download optimisation, not a price signal or survivor-performance filter.
        spots=[x[1] for x in spot if a<=x[0][:10]<=b]
        if not spots:continue
        options=[x for x in options if min(spots)-2000<=x['strike']<=max(spots)+2000]
        for c in options+fs:
            if int(c['lot_size'])<1:continue
            ca=max(a,(date.fromisoformat(expiry)-timedelta(days=14)).isoformat()) if c['option_type']!='FUT' else a
            if ca>b:continue
            count+=1
            if count>3500:raise ValueError('Download limit reached; choose a shorter range. Completed downloads are cached.')
            update(phase='Downloading expired NIFTY contracts',contracts=count,expiry=expiry)
            download(c['instrument_key'],ca,b,token)
            with closing(database()) as db,db:
                db.execute('INSERT OR REPLACE INTO contracts VALUES(?,?)',(c['instrument_key'],json.dumps(c)))
            contracts.append(c)
    return dict(start=start,end=end,contracts=len(contracts),source='Upstox historical one-minute OHLCV/OI',
                universe='Expired contracts only; option strikes within 2,000 points of observed spot opens; 2–14 calendar days to expiry. Active/unreturned expiries are not covered.')


def frames(start,end):
    """Load one session at a time to bound memory; include only cached contracts."""
    with closing(database()) as db:
        contracts={r['key']:json.loads(r['payload']) for r in db.execute('SELECT * FROM contracts')}
    days=sorted({r[0][:10] for r in spot_rows(start,end)})
    for day in days:
        with closing(database()) as db:
            rows=db.execute('SELECT key,payload FROM candles WHERE at>=? AND at<? ORDER BY at,key',(day,day+'Z'))
            grouped={}
            for key,payload in rows:
                candle=json.loads(payload);at=candle[0]
                item=grouped.setdefault(at,dict(spot=None,contracts={}))
                if key==h.NIFTY_KEY:item['spot']=candle
                elif key in contracts:item['contracts'][key]=(contracts[key],candle)
        for at,frame in sorted(grouped.items()):
            if frame['spot']:yield p.timestamp(at),frame
