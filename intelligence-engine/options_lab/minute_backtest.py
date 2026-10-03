"""Explicit OHLC approximation, isolated from exact replay and all live balances.

Signal inputs are completed five-minute bars. Fills occur at a subsequent minute
open; stops/targets observe minute closes and exit at the next open. No invented
bid/ask, depth, exchange Greeks, or one-second frames are produced.
"""
import json
import os
import subprocess
import sys
import threading
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from . import paper_agents as p, spread_agents as s, regime_agents as r, minute_history as h
from .engine import _implied_volatility, _greeks

NAMES=(*s.NAMES,*r.NAMES)
VERSION='one-minute-approximation-v1'
TIMEOUT=3600
ASSUMPTIONS=[
 'Exploratory one-minute OHLC simulation, NOT recorded quote replay or live execution validation.',
 'Nine independent ₹1 lakh accounts, one whole-lot basket each, max two entries/day and ₹2,000 planned risk. Unlike forward research, accounts do not share capital or compete for contracts.',
 'Signals use completed five-minute spot OHLC. Entries use the following minute open. Stops and targets are checked at minute closes and exit at the following open; intraminute paths and simultaneous leg execution are unknown.',
 'No historical bid/ask or depth is available. Fill assumptions: 0.5% adverse slippage per option leg, 0.02% for futures, plus current dated charges. Stress reruns double both slippage and fees.',
 'IV and delta are BSM estimates from completed option/spot closes, assumed 5.5% rate and zero yield, not historical exchange Greeks. Prior daily IV is derived only from earlier sessions in this dataset.',
 'Futures VWAP is a cumulative typical-price/volume approximation, not exchange average traded price. Full notional reserve may exceed ₹1 lakh.',
 'Historical event reviews are explicit retrospective admin assumptions. Missing reviews, IV, candles or hedge legs block entries; missing exits leave unresolved results.',
 'Only returned expired-contract history is tested. Download universe is bounded. No interpolation, synthetic candles, or substitution with current contracts. No independent holdout or profitability claim.'
]


def config(start,end,calendars=None):
    from .replay import request_config
    try:
        a=date.fromisoformat(start);b=date.fromisoformat(end)
        if a>b or (b-a).days>180 or b>=datetime.now(p.IST).date():raise ValueError()
    except (ValueError,TypeError):raise ValueError('Choose completed past dates spanning at most 180 days')
    # Reuse strict timezone/window validation in chunks, without its 60-day limit.
    reviews={}
    if not isinstance(calendars or [],list) or len(calendars or [])>181:raise ValueError('Too many event reviews')
    for item in calendars or []:
        day=item.get('date','')
        if not start<=day<=end or day in reviews:raise ValueError('Invalid or duplicate historical review date')
        reviews.update(request_config(day,day,[item])['calendars'])
    return dict(start=start,end=end,calendars=reviews)


def fill(legs,frame,field,at,entry=True,multiplier=1):
    fills=[]
    for leg in legs:
        data=frame['contracts'].get(leg['instrument_key'])
        if not data:return None
        meta,candle=data
        if any(meta.get(k)!=leg.get(k) for k in ('lot_size','option_type','strike','expiry')):return None
        side=leg['side'] if entry else ('SELL' if leg['side']=='BUY' else 'BUY')
        future=leg['option_type']=='FUT';slip=(.0002 if future else .005)*multiplier
        price=candle[1 if field=='open' else 4]*(1+slip if side=='BUY' else 1-slip)
        charges={k:v*multiplier for k,v in r.charges(price*leg['lot_size'],side,future).items()}
        fills.append(dict(**{k:leg[k] for k in ('instrument_key','option_type','strike','expiry','lot_size')},
                          side=side,price=price,quote_at=at.isoformat(),charges=charges))
    return fills


def pnl(pos,exits):
    gross=sum((b['price']-a['price'])*a['lot_size']*(1 if a['side']=='BUY' else -1) for a,b in zip(pos['legs'],exits))
    fees=sum(x['charges']['total'] for x in pos['legs']+exits)
    return gross-fees,fees


def signal_rows(frame,at,vwaps):
    spot=frame['spot'][4];out=[]
    for meta,candle in frame['contracts'].values():
        dte=(date.fromisoformat(meta['expiry'])-at.date()).days
        if candle[5]<=0 or candle[6]<=0 or not (0<dte<=35 if meta['option_type']=='FUT' else 2<=dte<=14):continue
        row=dict(meta,spot=spot,ltp=candle[4],iv=None,greeks={})
        if meta['option_type']=='FUT':
            value,volume=vwaps.get(meta['instrument_key'],(0,0));row['vwap']=value/volume if volume else None
        else:
            expiry=datetime.fromisoformat(meta['expiry']+'T15:30:00+05:30')
            years=(expiry-at).total_seconds()/(365*86400);kind='call' if meta['option_type']=='CE' else 'put'
            iv=_implied_volatility(candle[4],kind,spot,meta['strike'],years,.055,0.)
            if iv and 0<iv<2:
                row['iv']=100*iv
                row['greeks']=_greeks(kind,spot,meta['strike'],years,.055,0.,iv)
        out.append(row)
    return out


def simulate(frames,start,end,reviews,multiplier=1):
    accounts={name:dict(cash=100000.,peak=100000.,drawdown=0.,position=None,pending=None,
        exit_pending=None,trades=[],reasons=Counter(),entries=0,daily_start=100000.,eligible_bars=0,
        blocked=False,signals=0) for name in NAMES}
    state=r.fresh();group=[];previous=None;current_day=None;iv_today=None;vwaps={};observed=set();gaps=0;bar_count=0
    for now,frame in frames:
        day=now.date().isoformat();selected=start<=day<=end;minute=now.hour*60+now.minute
        if not 555<=minute<930:continue
        newday=day!=current_day
        gap=previous is not None and not newday and (now-previous).total_seconds()!=60
        if newday:
            if iv_today:state['iv_history']=(state['iv_history']+[iv_today])[-60:]
            iv_today=None;vwaps={};group=[];state['session_bars']=0
            for a in accounts.values():a.update(entries=0,daily_start=a['cash'])
        if gap:
            gaps+=int(selected);group=[];state['session_bars']=0
        if selected:observed.add(day)
        state['calendar']=reviews.get(day,dict(date=None,windows=[]))
        event=r.event_state(state['calendar'],now)
        # Only the minute OPEN is available to the fill phase. Decisions from
        # this minute's high/low/close/volume cannot affect these fills.
        for name,a in accounts.items():
            if a['blocked']:continue
            pos=a['position']
            if pos and (newday or gap):a['blocked']=True;a['reasons']['Unresolved across missing minute/session']+=1;continue
            reason=a['exit_pending'] or ('Session exit' if pos and minute>=915 else None)
            if pos and name in r.NAMES and event in ('UNREVIEWED','BLACKOUT'):reason='Event exit'
            if pos and reason:
                exits=fill(pos['legs'],frame,'open',now,False,multiplier)
                if not exits:a['blocked']=True;a['reasons']['Missing next-open exit leg']+=1;continue
                profit,fees=pnl(pos,exits);a['cash']+=profit
                a['trades'].append(dict(entry_at=pos['entry_at'],signal_at=pos['signal_at'],exit_at=now.isoformat(),
                    legs=pos['legs'],exit_legs=exits,pnl=round(profit,2),fees=round(fees,2),reason=reason))
                a.update(position=None,exit_pending=None)
            pending=a['pending'];a['pending']=None
            if pending and not a['position'] and selected and not gap and not newday and minute<855 and (name not in r.NAMES or event not in ('UNREVIEWED','BLACKOUT')):
                fills=fill(pending['legs'],frame,'open',now,True,multiplier)
                t=(s.terms(fills,name,frame['spot'][1]) if name in s.NAMES else r.terms(fills,pending['ctx'])) if fills else None
                risk=(t.get('planned_risk',t.get('max_loss')) if t else None)
                if not t or risk is None or risk>2000 or t['reserve']>a['cash'] or a['entries']>=2 or a['cash']<=a['daily_start']-2000:
                    a['reasons']['Next-open fill / risk / reserve / daily limit rejected']+=1
                else:
                    a['position']=dict(**t,legs=fills,entry_at=now.isoformat(),signal_at=pending['at'])
                    a['entries']+=1
            pos=a['position'];equity=a['cash']
            if pos:
                exits=fill(pos['legs'],frame,'close',now+timedelta(minutes=1),False,multiplier)
                if not exits:a['blocked']=True;a['reasons']['Missing minute-close exit leg']+=1;continue
                profit,_=pnl(pos,exits);equity+=profit
                seconds=(now+timedelta(minutes=1)-p.timestamp(pos['entry_at'])).total_seconds()
                timeout=1800 if name in ('long_straddle','long_strangle','iron_fly') else 7200 if name in r.NAMES else float('inf')
                a['exit_pending']=('Daily loss' if equity<=a['daily_start']-2000 else 'Stop at minute close' if profit<=-pos['stop_loss'] else 'Target at minute close' if profit>=pos['target_profit'] else 'Time stop' if seconds>=timeout else None)
            a['peak']=max(a['peak'],equity);a['drawdown']=max(a['drawdown'],a['peak']-equity)
        # Candle-close processing begins here.
        for key,(meta,candle) in frame['contracts'].items():
            if meta['option_type']=='FUT':
                value,vol=vwaps.get(key,(0.,0.));vwaps[key]=(value+(candle[2]+candle[3]+candle[4])/3*candle[5],vol+candle[5])
        if group and int(now.timestamp())//300!=int(group[0][0].timestamp())//300:group=[]
        group.append((now,frame['spot']))
        if len(group)==5 and int(group[0][0].timestamp())%300==0 and (now-group[0][0]).total_seconds()==240:
            bars=[x[1] for x in group];bar=dict(at=int(group[0][0].timestamp()),open=bars[0][1],high=max(x[2] for x in bars),low=min(x[3] for x in bars),close=bars[-1][4])
            state['candles']=(state['candles']+[bar])[-100:];state['session_bars']+=1;bar_count+=int(selected)
            at=now+timedelta(minutes=1);rows=signal_rows(frame,at,vwaps);ctx=r.context(state,rows,at)
            if ctx.get('iv'):iv_today=dict(day=day,iv=ctx['iv'],at=at.isoformat(),available_at=at.isoformat(),unit='percent')
            if selected:
                for name,a in accounts.items():
                    if a['blocked'] or a['position'] or a['entries']>=2 or a['cash']<=a['daily_start']-2000:continue
                    amin=at.hour*60+at.minute
                    if not (615 if name in s.NAMES else 600)<=amin<855:continue
                    if name in s.NAMES:
                        if not rows or state['session_bars']<12:a['reasons']['Needs complete session bars and option candles']+=1;continue
                        if name=='volatility_credit' and not any(x.get('iv') for x in rows):a['reasons']['Missing estimated option IV']+=1;continue
                        a['eligible_bars']+=1;sig=s.setup(state['candles'],name)
                        legs=s.select_legs([x for x in rows if x['option_type']!='FUT'],sig,name,bar['close']) if sig else None
                        reason='No trend/pullback/volatility setup or matching candles'
                    else:
                        if len(state['candles'])<50 or state['session_bars']<3:a['reasons']['Needs 50 complete bars and three session bars']+=1;continue
                        if ctx['event'] in ('UNREVIEWED','BLACKOUT'):a['reasons']['Missing historical event review or blackout']+=1;continue
                        from .replay import IV_NAMES
                        if name in IV_NAMES and ctx.get('iv_percentile') is None:a['reasons']['Needs 20 prior daily estimated IV observations']+=1;continue
                        if name=='iron_fly' and ctx['event']!='POST_EVENT':a['reasons']['No reviewed post-event window']+=1;continue
                        if not any(x['option_type']==('FUT' if name=='futures_trend' else 'CE') for x in rows):a['reasons']['Missing matching contract candles']+=1;continue
                        a['eligible_bars']+=1;legs,reason=r.choose(name,ctx,rows,bar['close'],state['candles'])
                    if legs:
                        a['pending']=dict(legs=legs,ctx=ctx,at=at.isoformat());a['signals']+=1
                    else:a['reasons'][reason]+=1
            group=[]
        previous=now;current_day=day
    output={}
    for name,a in accounts.items():
        incomplete=a['blocked'] or bool(a['position']);tested=bool(a['eligible_bars'])
        trades=a['trades'];profit=sum(t['pnl'] for t in trades)
        output[name]=dict(status='unresolved' if incomplete else 'approximate' if tested else 'not_testable',
            closed_trades=len(trades) if tested else None,net_pnl=round(profit,2) if tested and not incomplete else None,
            closed_only_pnl=round(profit,2),fees=round(sum(t['fees'] for t in trades),2),
            max_drawdown=round(a['drawdown'],2) if tested and not incomplete else None,
            win_rate=round(100*sum(t['pnl']>0 for t in trades)/len(trades),2) if trades else None,
            eligible_bars=a['eligible_bars'],signals=a['signals'],reasons=dict(a['reasons']),trades=trades,
            unresolved_position=a['position'] if incomplete else None)
    return dict(strategies=output,observed_days=sorted(observed),complete_bars=bar_count,missing_minute_gaps=gaps)


def update(job,**values):
    with closing(h.database()) as db,db:
        db.execute("UPDATE jobs SET progress=?,updated=? WHERE id=? AND status IN ('queued','running')",(json.dumps(values),datetime.now(timezone.utc).isoformat(),job))


def dashboard():
    from .evidence_archive import status
    with closing(h.database()) as db,db:
        db.execute("UPDATE jobs SET status='failed',error='Interrupted or exceeded one-hour limit; retry using cached downloads' WHERE status IN ('queued','running') AND at<?",((datetime.now(timezone.utc)-timedelta(seconds=TIMEOUT+60)).isoformat(),))
        row=db.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 1').fetchone()
        latest=db.execute("SELECT result FROM jobs WHERE status='completed' ORDER BY id DESC LIMIT 1").fetchone()
    job=dict(row) if row else None
    if job:
        for k in ('config','progress','result'):job[k]=json.loads(job[k]) if job[k] else None
        job.pop('result',None)
    return dict(job=job,result=json.loads(latest[0]) if latest else None,retention=status(),assumptions=ASSUMPTIONS)


def submit(start,end,calendars=None):
    cfg=config(start,end,calendars);dashboard();at=datetime.now(timezone.utc).isoformat()
    with closing(h.database()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running')").fetchone():raise ValueError('A minute backtest is already running')
        job=db.execute('INSERT INTO jobs(at,updated,status,config,progress) VALUES(?,?,?,?,?)',(at,at,'queued',json.dumps(cfg),'{}')).lastrowid
    threading.Thread(target=launch,args=(job,),daemon=True).start()
    return dict(job_id=job,status='queued')


def failure(job,message):
    with closing(h.database()) as db,db:db.execute("UPDATE jobs SET status='failed',error=? WHERE id=? AND status IN ('queued','running')",(message,job))


def launch(job):
    try:
        proc=subprocess.run([sys.executable,'-m','options_lab.minute_backtest',str(job)],cwd=Path(__file__).resolve().parent.parent,
            timeout=TIMEOUT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if proc.returncode:failure(job,'Minute worker failed; cached downloads and live accounts retained')
    except Exception:failure(job,'Minute worker interrupted or exceeded one hour; retry a shorter range')


def worker(job):
    with closing(h.database()) as db,db:
        row=db.execute("SELECT config FROM jobs WHERE id=? AND status='queued'",(job,)).fetchone()
        if not row:return
        cfg=json.loads(row[0]);db.execute("UPDATE jobs SET status='running' WHERE id=?",(job,))
    try:
        coverage=h.collect(cfg,lambda **x:update(job,**x))
        update(job,phase='Simulating minute-open fills and minute-close exits')
        result=simulate(h.frames(coverage['start'],coverage['end']),cfg['start'],cfg['end'],cfg['calendars'])
        update(job,phase='Rerunning with doubled slippage and fees')
        stress=simulate(h.frames(coverage['start'],coverage['end']),cfg['start'],cfg['end'],cfg['calendars'],2)
        for name,a in result['strategies'].items():
            a['stress_net_pnl']=stress['strategies'][name]['net_pnl'];a['stress_status']=stress['strategies'][name]['status']
        result.update(version=VERSION,mode='one_minute_approximate',start=cfg['start'],end=cfg['end'],coverage=coverage,
            historical_review_dates=sorted(cfg['calendars']),assumptions=ASSUMPTIONS,completed_at=datetime.now(timezone.utc).isoformat(),live_trading_approved=False)
        with closing(h.database()) as db,db:
            db.execute("UPDATE jobs SET status='completed',result=?,progress=? WHERE id=? AND status='running'",(json.dumps(result),json.dumps(dict(phase='Complete')),job))
    except Exception as exc:
        # Token and provider response bodies are deliberately excluded.
        message=str(exc) if isinstance(exc,ValueError) else 'Upstox history unavailable. Check token and Upstox Plus access; completed downloads are cached.'
        failure(job,message[:300])


if __name__=='__main__':
    try:os.nice(10)
    except (OSError,AttributeError):pass
    worker(int(sys.argv[1]))
