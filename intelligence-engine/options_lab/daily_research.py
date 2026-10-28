"""Daily NIFTY direction experiments. No derivatives fills or broker orders.

Official EOD reports only. Signals at close execute at the NEXT recorded open.
Returns are unlevered index-reference returns, not tradable option/future P&L.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import urllib.request
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from . import paper_agents as p

SOURCE = 'https://www.niftyindices.com/reports/historical-data'
ARCHIVE = 'https://nsearchives.nseindia.com/content/indices/ind_close_all_{day}.csv'
SEED = Path(__file__).with_name('reference_data') / 'nifty_daily_ohlc.json'
NAMES = {'daily_trend':'Daily EMA50/200 trend', 'daily_breakout':'Daily 20/10 channel breakout',
         'daily_pullback':'Daily RSI2 pullback', 'daily_momentum':'Daily 63-session momentum'}
RULES = {'daily_trend':'Long when close > EMA50 > EMA200; short when close < EMA50 < EMA200; otherwise flat.',
 'daily_breakout':'Enter above the previous 20-session high / below its low; exit at the opposite 10-session channel.',
 'daily_pullback':'When close is above EMA200, buy RSI2 < 10; exit RSI2 > 60 or after five sessions. Long only.',
 'daily_momentum':'Long when the 63-session return is positive and close > EMA200; short for the opposite; otherwise flat.'}


def parse_csv(text):
    rows=[]
    for raw in csv.DictReader(io.StringIO(text.lstrip('\ufeff'))):
        r={k.strip().lower():str(v or '').strip() for k,v in raw.items() if k}
        name=r.get('index name',r.get('index','NIFTY 50')).upper()
        if name!='NIFTY 50':continue
        day=r.get('index date',r.get('date',''))
        for fmt in ('%d-%m-%Y','%d-%b-%Y','%d %b %Y','%Y-%m-%d'):
            try:day=datetime.strptime(day,fmt).date().isoformat();break
            except ValueError:pass
        rows.append(dict(date=day,**{k:r.get(k,r.get(('closing' if k=='close' else k)+' index value','')) for k in ('open','high','low','close')}))
    return validate(rows)


def validate(rows):
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError('Supply at most 10,000 daily rows')
    result={}
    today=datetime.now(p.IST).date()
    for r in rows:
        d=date.fromisoformat(r['date'])
        if d>=today:raise ValueError('Only completed prior trading dates can be imported')
        values={k:float(str(r[k]).replace(',','')) for k in ('open','high','low','close')}
        if not all(math.isfinite(v) and v>0 for v in values.values()):raise ValueError('Invalid daily price')
        if not values['low']<=min(values['open'],values['close'])<=max(values['open'],values['close'])<=values['high']:raise ValueError('Invalid daily OHLC ordering')
        item=dict(date=d.isoformat(),**values)
        if item['date'] in result and result[item['date']]!=item:raise ValueError('Conflicting duplicate date')
        result[item['date']]=item
    if not result:raise ValueError('No valid NIFTY 50 rows')
    return sorted(result.values(),key=lambda r:r['date'])


def schema(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS nifty_daily_bars(day TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS nifty_daily_imports(id INTEGER PRIMARY KEY,at TEXT NOT NULL,source TEXT NOT NULL,sha TEXT NOT NULL,rows INTEGER NOT NULL);
''')


def store(rows, source, db):
    rows=validate(rows);schema(db)
    for r in rows:
        old=db.execute('SELECT payload FROM nifty_daily_bars WHERE day=?',(r['date'],)).fetchone()
        if old and json.loads(old[0])!=r:raise ValueError('Existing date differs; source correction requires review')
    for r in rows:db.execute('INSERT OR IGNORE INTO nifty_daily_bars VALUES(?,?)',(r['date'],json.dumps(r)))
    db.execute('INSERT INTO nifty_daily_imports(at,source,sha,rows) VALUES(?,?,?,?)',
        (datetime.now(timezone.utc).isoformat(),source,hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),len(rows)))
    return len(rows)


def load(db):
    schema(db)
    if SEED.exists():
        seed=json.loads(SEED.read_text())
        if not db.execute('SELECT 1 FROM nifty_daily_imports WHERE sha=?',(seed['sha256'],)).fetchone():
            store(seed['rows'],seed['source'],db)
    return [json.loads(r[0]) for r in db.execute('SELECT payload FROM nifty_daily_bars ORDER BY day')]


def ema(values,n):
    if len(values)<n:return None
    result=sum(values[:n])/n
    for x in values[n:]:result+=(x-result)*2/(n+1)
    return result


def rsi(values,n=2):
    if len(values)<=n:return None
    changes=[b-a for a,b in zip(values,values[1:])]
    up=sum(max(x,0) for x in changes[:n])/n;down=sum(max(-x,0) for x in changes[:n])/n
    for x in changes[n:]:up=(up*(n-1)+max(x,0))/n;down=(down*(n-1)+max(-x,0))/n
    return 100*up/(up+down) if up+down else 50.


def features(rows):
    """Causal indicators in linear time; each item uses this close and older bars."""
    result=[];closes=[];e50=None;e200=None;up=down=0.
    for i,bar in enumerate(rows):
        close=bar['close'];closes.append(close)
        if i==49:e50=sum(closes)/50
        elif i>49:e50+=(close-e50)*2/51
        if i==199:e200=sum(closes)/200
        elif i>199:e200+=(close-e200)*2/201
        if i:
            change=close-closes[-2]
            if i<=2:up+=max(change,0)/2;down+=max(-change,0)/2
            else:up=(up+max(change,0))/2;down=(down+max(-change,0))/2
        prior=rows[max(0,i-20):i];exit_bars=rows[max(0,i-10):i]
        result.append(dict(ready=i>=399,close=close,ema50=e50,ema200=e200,
            rsi2=100*up/(up+down) if up+down else 50.,
            momentum=close-closes[-64] if i>=63 else 0,
            upper=max((r['high'] for r in prior),default=close),
            lower=min((r['low'] for r in prior),default=close),
            exit_upper=max((r['high'] for r in exit_bars),default=close),
            exit_lower=min((r['low'] for r in exit_bars),default=close)))
    return result


def direction(name,f,position,held):
    if name not in NAMES:raise ValueError('Unknown daily strategy')
    if not f or not f['ready']:return 0
    close=f['close'];e200=f['ema200']
    if name=='daily_trend':
        return 1 if close>f['ema50']>e200 else -1 if close<f['ema50']<e200 else 0
    if name=='daily_momentum':
        return 1 if close>e200 and f['momentum']>0 else -1 if close<e200 and f['momentum']<0 else 0
    if name=='daily_pullback':
        if position:return 0 if f['rsi2']>60 or held>=5 or close<e200 else position
        return int(close>e200 and f['rsi2']<10)
    if close>f['upper']:return 1
    if close<f['lower']:return -1
    if position==1 and close<f['exit_lower']:return 0
    if position==-1 and close>f['exit_upper']:return 0
    return position


def desired(name,bars,position,held):
    f=features(bars)
    return direction(name,f[-1] if f else None,position,held)


def study(rows, name, cost_bps=5, indicators=None):
    # Independent +/-1x reference exposure; open-to-open results contain overnight risk.
    equity=1.;peak=1.;dd=0.;pos=0;held=0;turnover=0;entry=None;trades=[];daily=[]
    indicators=indicators if indicators is not None else features(rows)
    for i in range(400,len(rows)):
        new=direction(name,indicators[i-1],pos,held)
        turn=abs(new-pos);turnover+=turn
        before=equity
        if new!=pos and pos:equity*=1-cost_bps/10000
        if new!=pos:
            if entry:trades.append(dict(entry_date=entry['date'],exit_date=rows[i]['date'],direction=pos,return_pct=round((equity/entry['equity']-1)*100,4)))
            entry=dict(date=rows[i]['date'],equity=equity) if new else None
            if new:equity*=1-cost_bps/10000
            held=0
        pos=new;held=held+1 if pos else 0
        if i==len(rows)-1:
            if daily:
                daily[-1]['ending_rebalance_cost_pct']=(equity/before-1)*100
                daily[-1]['return_pct']=((1+daily[-1]['return_pct']/100)*(equity/before)-1)*100
            peak=max(peak,equity);dd=max(dd,(peak-equity)/peak)
            break  # Final-open rebalance is charged; no future price is invented.
        move=rows[i+1]['open']/rows[i]['open']-1
        equity*=1+pos*move
        if equity<=0:raise ValueError('Reference equity exhausted')
        peak=max(peak,equity);dd=max(dd,(peak-equity)/peak)
        daily.append(dict(date=rows[i+1]['date'],signal_date=rows[i-1]['date'],position=pos,return_pct=(equity/before-1)*100))
    return dict(name=NAMES[name],rule=RULES[name],reference_return_pct=round((equity-1)*100,3) if daily else None,
        max_drawdown_pct=round(dd*100,3) if daily else None,closed_trades=len(trades),open_exposure=pos,
        observations=len(daily),turnover_units=turnover,latest_signal=direction(name,indicators[-1] if indicators else None,pos,held),
        trades=trades[-100:],daily=daily,live_trading_approved=False)


def report(rows):
    gaps=[i for i in range(1,len(rows)) if (date.fromisoformat(rows[i]['date'])-date.fromisoformat(rows[i-1]['date'])).days>7]
    usable=rows[gaps[-1]:] if gaps else rows
    closes=[r['close'] for r in usable];indicators=features(usable)
    results={k:study(usable,k,indicators=indicators) for k in NAMES}
    for k,v in results.items():v['double_cost_return_pct']=study(usable,k,10,indicators)['reference_return_pct']
    benchmark=(usable[-1]['open']/usable[400]['open']-1)*100 if len(usable)>401 else None
    return dict(ok=True,version='nifty-daily-research-v1',source=SOURCE,timeframe='1 day',rows=len(rows),
        first=rows[0]['date'] if rows else None,last=rows[-1]['date'] if rows else None,
        ema50=ema(closes,50),ema200=ema(closes,200),warmup_required=400,usable_rows=len(usable),
        test_start=usable[400]['date'] if len(usable)>401 else None,
        test_end=usable[-1]['date'] if len(usable)>401 else None,
        missing_calendar_gaps=[dict(after=a['date'],before=b['date']) for a,b in zip(rows,rows[1:]) if (date.fromisoformat(b['date'])-date.fromisoformat(a['date'])).days>7],
        benchmark_return_pct=round(benchmark,3) if benchmark is not None else None,strategies=results,
        method='Retrospective daily index-direction study; next recorded open execution; 5 bps per exposure leg, 10 bps stress. Returns stop at the final open, including its rebalance costs. Gaps over seven calendar days restart warm-up; shorter missing sessions are not independently audited. Synthetic daily-rebalanced +/-1x index exposure. No dividends, financing, derivatives P&L, broker margin, option decay, or live fills simulated. Historical reports may contain later corrections. No held-out validation.',
        automatic_fetch_enabled=False)


def dashboard():
    with closing(p.database()) as db:
        rows=load(db);db.commit()
    return report(rows)


def import_csv(text):
    if not isinstance(text,str) or len(text)>2_000_000:raise ValueError('CSV must be at most 2 MB')
    rows=parse_csv(text)
    with closing(p.database()) as db:
        with db:written=store(rows,'Admin-supplied NSE/NSE Indices CSV (origin asserted by uploader)',db)
    return dict(ok=True,imported=written)


def refresh(day=None):
    # One fixed official report per day; no cookie/proxy bypass or endpoint crawling.
    day=day or (datetime.now(p.IST).date()-timedelta(days=1))
    if day>=datetime.now(p.IST).date():raise ValueError('Only completed prior dates')
    url=ARCHIVE.format(day=day.strftime('%d%m%Y'))
    request=urllib.request.Request(url,headers={'User-Agent':'AGI-Research/1.0','Accept':'text/csv'})
    with urllib.request.urlopen(request,timeout=15) as response:
        text=response.read(2_000_001).decode('utf-8-sig')
    if len(text)>2_000_000:raise ValueError('Daily report too large')
    rows=parse_csv(text)
    if any(r['date']!=day.isoformat() for r in rows):raise ValueError('Report date mismatch')
    with closing(p.database()) as db:
        with db:store(rows,url,db)
    return dict(ok=True,imported=len(rows),date=day.isoformat())
