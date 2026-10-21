"""Automatic evidence checks and frozen retrospective tests; no broker orders.

Never changes strategy rules, event reviews, live positions or provider routing.
"""
import hashlib
import json
import os
import sqlite3
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from . import data_evidence as e, year_history as y, paper_agents as p, minute_history as mh

VERSION='data-validation-v1'


def age(value,now):
    try:return (now-p.timestamp(value)).total_seconds()
    except (ValueError,TypeError):return None


def stream_check(now=None):
    now=now or datetime.now(timezone.utc)
    with closing(p.database()) as db:
        row=db.execute('SELECT payload FROM stream_status WHERE id=1').fetchone()
        session=db.execute('SELECT enabled,state FROM sessions WHERE id=1').fetchone()
    up=json.loads(row[0]) if row else {};gr=e.read('groww_stream')
    result={}
    for name,state,key in [('upstox',up,'last_message_at'),('groww',gr,'last_received_at')]:
        seconds=age(state.get(key),now)
        heartbeat=age(state.get('heartbeat_at'),now)
        fresh=seconds is not None and 0<=seconds<=10 and heartbeat is not None and 0<=heartbeat<=90
        if name=='groww':fresh=fresh and (state.get('fresh_messages') or 0)>0 and (age(state.get('last_exchange_at'),now) is not None and 0<=age(state.get('last_exchange_at'),now)<=10)
        else:fresh=fresh and bool(state.get('connected')) and (state.get('fresh_contracts') or 0)>0
        result[name]=dict(fresh=fresh,receipt_age_seconds=seconds,heartbeat_age_seconds=heartbeat,status=state.get('status','unavailable'))
    # Retain the first actual fresh verification separately from socket authorization.
    proof=e.read('fresh_stream_proof')
    for name,item in result.items():
        if item['fresh']:proof[name]=dict(last_verified_at=now.isoformat(),**item)
    if proof:e.write('fresh_stream_proof',proof)
    diagnostics={}
    if session:
        state=json.loads(session['state'])
        groups={'legacy':state.get('agents',{}),**{k:state.get(k,{}).get('agents',{}) for k in ('spreads','research','news_agent')}}
        for group,agents in groups.items():
            for name,a in agents.items():
                diagnostics[group+':'+name]=dict(status=a.get('status'),blocked=bool(a.get('blocked')),open_position=bool(a.get('position')),closed_trades=len(a.get('trades',[])),closed_pnl=round(sum(t.get('pnl',0) for t in a.get('trades',[])),2),latest_events=a.get('events',[])[-3:])
    report=dict(at=now.isoformat(),feeds=result,fresh_stream_proof=proof,paper_enabled=bool(session and session['enabled']),agents=diagnostics,live_orders=False)
    e.write('live_validation',report)
    # Store changing decision summaries with timestamps for later attribution.
    with sqlite3.connect(e.root()/'validation_log.sqlite3',timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS decisions(at TEXT PRIMARY KEY,payload TEXT)')
        db.execute('INSERT OR IGNORE INTO decisions VALUES(?,?)',(now.replace(second=0,microsecond=0).isoformat(),json.dumps(report)))
        db.execute('DELETE FROM decisions WHERE at<?',((now-timedelta(days=365)).isoformat(),))
    return report


def compare_spot():
    """Compare identical IST minute timestamps, never compare differently timed quotes."""
    by={}
    with closing(y.db()) as db:
        for provider,key in [('upstox','NSE_INDEX|Nifty 50'),('groww','NSE-NIFTY')]:
            by[provider]={at:json.loads(payload) for at,payload in db.execute('SELECT at,payload FROM candles WHERE provider=? AND instrument=?',(provider,key)) if '09:15'<at[11:16]<'15:30' or at[11:16]=='09:15'}
        gaps=[dict(provider=pv,reason=reason,chunks=n) for pv,reason,n in db.execute('SELECT provider,reason,COUNT(*) FROM gaps GROUP BY provider,reason')]
    shared=sorted(by['upstox'].keys()&by['groww'].keys());diff=[];examples=[]
    for at in shared:
        a,b=by['upstox'][at],by['groww'][at];points=abs(a[4]-b[4]);bps=points/a[4]*10000
        diff.append(bps)
        if bps>5 and len(examples)<20:examples.append(dict(at=at,upstox_close=a[4],groww_close=b[4],difference_bps=round(bps,3)))
    diff.sort();sessions={}
    for provider,rows in by.items():
        counts=Counter(at[:10] for at in rows)
        sessions[provider]=dict(candles=len(rows),observed_sessions=len(counts),sessions_with_375_minutes=sum(n==375 for n in counts.values()),short_sessions={d:n for d,n in counts.items() if n!=375},unmatched_minutes=len(rows.keys()-by['groww' if provider=='upstox' else 'upstox'].keys()))
    report=dict(at=datetime.now(timezone.utc).isoformat(),matched_minutes=len(shared),median_difference_bps=round(diff[len(diff)//2],4) if diff else None,max_difference_bps=round(max(diff),4) if diff else None,above_5bps=sum(x>5 for x in diff),examples=examples,sessions=sessions,gaps=gaps,
        limitations='Spot only. Unmatched timestamps are missing comparisons, not zero differences. Short sessions need exchange-calendar reconciliation; no holiday assumptions. Derivative depth is not in historical candles.')
    e.write('data_comparison',report);return report


def reviews():
    from .replay import schema
    with closing(p.database()) as db:
        schema(db);rows=db.execute('SELECT payload FROM paper_calendar_reviews ORDER BY id').fetchall()
    result={}
    for row in rows:
        item=json.loads(row[0]);result[item['date']]=item
    return result


def compact(result):
    return {**{k:v for k,v in result.items() if k!='strategies'},'strategies':{n:{k:v for k,v in a.items() if k not in ('trades','unresolved_position')} for n,a in result['strategies'].items()}}


def refresh_candidates(report=None):
    """Re-evaluate operational gates without re-optimising any strategy."""
    report=report or e.read('strategy_validation')
    if report.get('status')!='complete':return report
    quality=e.read('data_comparison');live=e.read('live_validation');blockers=[]
    if not quality.get('matched_minutes'):blockers.append('Provider comparison has no matched minutes')
    if any(x['provider']=='upstox' for x in quality.get('gaps',[])):blockers.append('Unresolved Upstox historical gaps')
    if quality.get('above_5bps',0):blockers.append('Provider price discrepancies need review')
    if not all(live.get('feeds',{}).get(k,{}).get('fresh') for k in ('upstox','groww')):blockers.append('Both feeds need current fresh-session verification')
    if not live.get('paper_enabled'):blockers.append('Paper engine is not enabled')
    candidates=report.get('statistical_candidates',[])
    report.update(promotion_blockers=blockers,paper_candidates=[] if blockers else candidates)
    e.write('strategy_validation',report)
    # A watchlist observes existing independent paper accounts; it never resets them.
    e.write('paper_watchlist',dict(at=datetime.now(timezone.utc).isoformat(),candidates=report['paper_candidates'],
        blockers=blockers,agents={k:v for k,v in live.get('agents',{}).items() if k.split(':',1)[-1] in candidates},live_orders=False))
    return report


def run_experiment():
    from . import minute_backtest as mb
    cfg=e.read('config');a,b=cfg['start'],cfg['end'];signature=hashlib.sha256((VERSION+a+b).encode()).hexdigest()
    previous=e.read('strategy_validation')
    if previous.get('signature')==signature and previous.get('status')=='complete':return refresh_candidates(previous)
    # Freeze split before results; never retune to the later period.
    days=sorted({x[0][:10] for x in mh.spot_rows(a,b)})
    if len(days)<80:
        result=dict(status='blocked',reason='Need at least 80 observed spot sessions',observed_sessions=len(days));e.write('strategy_validation',result);return result
    split=days[int(len(days)*.75)];end_train=(p.timestamp(split+'T00:00:00+05:30')-timedelta(days=1)).date().isoformat()
    report=dict(status='running',signature=signature,version=VERSION,train=[a,end_train],validation=[split,b],started_at=datetime.now(timezone.utc).isoformat(),live_orders=False,
        limitations=['Chronological retrospective validation; these dates may have been inspected before, so not an untouched holdout.','Missing historical event reviews stay blocked; none are invented.','Nine one-minute approximations use identical costs, next-open fills and doubled-cost stress.','Legacy strategies use recorded snapshots separately; news requires point-in-time news evidence. No comparable synthetic history is invented.'])
    report['fill_assumptions']=mb.ASSUMPTIONS
    e.write('strategy_validation',report);rs=reviews()
    # Whole-year warm-up frames precede each selected window; warm-up cannot enter.
    outputs={}
    for label,start,end in [('train',a,end_train),('validation',split,b)]:
        for stress in (1,2):
            report['phase']=f'{label}: cost multiplier {stress}';e.write('strategy_validation',report)
            checkpoint='experiment_'+label+('_stress' if stress==2 else '')
            saved=e.read(checkpoint)
            result=saved['result'] if saved.get('signature')==signature else mb.simulate(mh.frames(a,end),start,end,rs,stress)
            # Keep trade-level evidence on persistent storage, not just aggregate P&L.
            e.write(checkpoint,dict(signature=signature,result=result))
            outputs[label+('_stress' if stress==2 else '')]=compact(result)
    train=outputs['train']['strategies'];valid=outputs['validation']['strategies'];stress=outputs['validation_stress']['strategies']
    selected=[n for n,v in train.items() if v['status']=='approximate' and (v.get('closed_trades') or 0)>=30 and (v.get('net_pnl') or 0)>0 and (outputs['train_stress']['strategies'][n].get('net_pnl') or 0)>0]
    candidates=[n for n in selected if valid[n]['status']=='approximate' and (valid[n].get('closed_trades') or 0)>=30 and (valid[n].get('net_pnl') or 0)>0 and (stress[n].get('net_pnl') or 0)>0]
    compare_spot()
    report['statistical_candidates']=candidates
    report.update(status='complete',completed_at=datetime.now(timezone.utc).isoformat(),results=outputs,selected_on_training=selected,paper_candidates=candidates,
        paper_policy='Existing paper accounts retained; candidates monitored in decision log. No automatic rule changes, allocation, live orders or clearing of unresolved positions.',
        news_status='Requires recorded point-in-time news; not tested by price-only minute history')
    refresh_candidates(report)
    # Original baselines: use only actual stored quote snapshots, separate cost model.
    try:
        start=max(a,(p.timestamp(b+'T00:00:00+05:30')-timedelta(days=29)).date().isoformat())
        e.write('legacy_validation',p.backtest(start,b))
    except Exception as exc:e.write('legacy_validation',dict(status='blocked',reason=type(exc).__name__,mode='recorded snapshot replay'))
    return report


def cycle():
    stream_check()
    last=e.read('data_comparison');seconds=age(last.get('at'),datetime.now(timezone.utc))
    if seconds is None or seconds>3600:compare_spot()
    refresh_candidates()


if __name__=='__main__':
    import sys
    try:os.nice(10);lock=e.process_lock('validation_'+('experiment' if len(sys.argv)>1 and sys.argv[1]=='experiment' else 'monitor'))
    except BlockingIOError:sys.exit(0)
    if len(sys.argv)>1 and sys.argv[1]=='experiment':
        try:run_experiment()
        except Exception as exc:e.write('strategy_validation',dict(status='failed',reason=type(exc).__name__,at=datetime.now(timezone.utc).isoformat(),live_orders=False))
    else:
        while True:
            try:cycle()
            except Exception as exc:e.write('validation_error',dict(type=type(exc).__name__,at=datetime.now(timezone.utc).isoformat()))
            time.sleep(60)
