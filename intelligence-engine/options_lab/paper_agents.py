"""Deterministic, quote-sampled NIFTY experiments. No broker execution imports.

Signal at t, hypothetical buy at the next recorded quote. Live and replay use
one transition function. Only the existing collector writes source quotes.
"""
from __future__ import annotations
import json
import math
import os
import zlib
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
VERSION = 'nifty-paper-v1.1'
STRATEGIES = ('opening_range', 'mean_reversion')
POLICY = dict(capital=100000, max_premium=10000, daily_loss=2000,
              stop_pct=20, target_pct=40, slippage_pct=0.5,
              cost_pct=0.5, fixed_cost=20, max_trades_per_day=2)


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone-aware timestamps required')
    return result


def fresh_state():
    return dict(version=VERSION, policy=dict(POLICY), last_at=None, day=None,
                history=[], agents={key: dict(cash=100000, position=None,
                pending=None, trades=[], events=[], daily_start=100000,
                daily_entries=0, peak=100000, max_drawdown=0, equity=100000,
                blocked=False, status='Waiting for quotes') for key in STRATEGIES})


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def valid_quote(row):
    b, a, lot, vol, oi = [number(row.get(k)) for k in ('bid', 'ask', 'lot_size', 'volume', 'oi')]
    return (b is not None and a is not None and 0 < b <= a
            and (a-b)/a <= .05 and lot is not None and lot >= 1 and lot == int(lot)
            and vol is not None and vol > 0 and oi is not None and oi > 0)


def event(agent, at, kind, reason):
    agent['status'] = reason
    agent['events'].append(dict(at=at, kind=kind, reason=reason))
    agent['events'] = agent['events'][-100:]


def fee(notional, policy):
    return policy['fixed_cost'] + notional * policy['cost_pct'] / 100


def direction(strategy, history, spot):
    if strategy == 'opening_range':
        opening = [h for h in history if h['minute'] <= 585]
        if {h['minute'] // 15 for h in opening} != {37, 38, 39}:
            return None
        upper, lower = max(h['spot'] for h in opening), min(h['spot'] for h in opening)
        if spot > upper * 1.001:
            return 'CE'
        if spot < lower * .999:
            return 'PE'
    elif len(history) >= 6:
        window = [h['spot'] for h in history[-6:]]
        average = sum(window) / len(window)
        sd = math.sqrt(sum((s-average)**2 for s in window) / len(window))
        # Demand both a two-standard-deviation displacement and 0.2% distance.
        if sd > 0 and spot < average - max(2*sd, average*.002):
            return 'CE'
        if sd > 0 and spot > average + max(2*sd, average*.002):
            return 'PE'
    return None


def step(state, rows, *, wall_now=None, allow_entries=True, interval_seconds=900):
    """Atomic simulated transition; caller persists the state and source cursor."""
    if interval_seconds not in (1, 900):
        raise ValueError('Supported observation intervals are 1 and 900 seconds')
    fast = interval_seconds == 1
    max_gap = 5 if fast else 1200
    if not rows:
        return
    at = rows[0]['captured_at']
    now = timestamp(at)
    if state['last_at'] and now <= timestamp(state['last_at']):
        return
    rows = [r for r in rows if r.get('underlying_key') == 'NSE_INDEX|Nifty 50'
            and r.get('provider') == 'upstox' and r.get('captured_at') == at]
    spots = [number(r.get('spot')) for r in rows]
    spots = [s for s in spots if s is not None and s > 0]
    if not spots:
        return
    local = now.astimezone(IST)
    minute = local.hour * 60 + local.minute
    if local.weekday() >= 5 or not 555 <= minute <= 930:
        return
    # Multiple collectors/retries can write distinct timestamps in one window.
    # Use only its first observation; later repetitions cannot accelerate signals
    # or fills, or crowd earlier opening observations out of the history.
    if state['last_at'] and int(now.timestamp()) // interval_seconds == int(timestamp(state['last_at']).timestamp()) // interval_seconds:
        return
    day = local.date().isoformat()
    gap = bool(state['last_at'] and (now - timestamp(state['last_at'])).total_seconds() > max_gap)
    new_day = state['day'] != day
    stale = wall_now is not None and not 0 <= (wall_now-now).total_seconds() <= (5 if fast else 180)
    spot = sorted(spots)[len(spots)//2]
    inconsistent = (max(spots)-min(spots))/spot > .002
    if new_day or gap or inconsistent or stale:
        state['history'] = []
    if new_day:
        for agent in state['agents'].values():
            agent['daily_start'] = agent['equity']
            agent['daily_entries'] = 0
            agent['pending'] = None
    quotes = {r['instrument_key']: r for r in rows if valid_quote(r)
              and (not fast or (r.get('quote_at') and
                   0 <= (now-timestamp(r['quote_at'])).total_seconds() <= 5))}
    policy = state['policy']
    for name, agent in state['agents'].items():
        pos = agent['position']
        if pos and (gap or new_day or stale or inconsistent):
            agent['blocked'] = True
            agent['pending'] = None
            event(agent, at, 'data_gap', 'Open position unresolved across missing/stale quotes; agent halted')
        if agent['blocked']:
            continue
        if pos:
            quote = quotes.get(pos['instrument_key'])
            if not quote:
                agent['blocked'] = True
                event(agent, at, 'data_gap', 'Open contract has no usable two-sided quote; agent halted')
                continue
            exit_price = float(quote['bid']) * (1-policy['slippage_pct']/100)
            proceeds = exit_price*pos['quantity']
            equity = agent['cash'] + proceeds - fee(proceeds, policy)
            pnl = equity - pos['equity_before']
            move = (exit_price / pos['entry_price'] - 1)*100
            reason = ('Session exit' if minute >= 915 else 'Daily loss limit' if equity <= agent['daily_start']-policy['daily_loss']
                      else 'Premium stop' if move <= -policy['stop_pct'] else 'Premium target' if move >= policy['target_pct'] else None)
            agent['equity'] = equity
            if reason:
                agent['cash'] = equity
                trade = dict(**pos, exit_at=at, exit_price=round(exit_price,4),
                             exit_cost=round(fee(proceeds,policy),2), pnl=round(pnl,2), reason=reason)
                agent['trades'].append(trade)
                agent['position'] = None
                event(agent, at, 'exit', reason)
        elif agent['pending']:
            pending = agent['pending']
            agent['pending'] = None
            quote = quotes.get(pending['instrument_key'])
            if (allow_entries and not stale and not gap and not inconsistent and minute < 870 and quote
                and (now-timestamp(pending['signal_at'])).total_seconds() <= max_gap
                and (not fast or timestamp(quote['quote_at']) > timestamp(pending['signal_at']))):
                entry = float(quote['ask']) * (1+policy['slippage_pct']/100)
                quantity = int(quote['lot_size'])  # Never split an exchange lot.
                premium = entry*quantity
                cost = fee(premium,policy)
                if premium+cost <= min(policy['max_premium'],agent['cash']) and agent['equity'] > agent['daily_start']-policy['daily_loss']:
                    agent['position'] = dict(instrument_key=quote['instrument_key'],
                        option_type=quote['option_type'], strike=quote['strike'], expiry=quote['expiry'],
                        signal_at=pending['signal_at'], entry_at=at, entry_price=entry,
                        quantity=quantity, entry_cost=cost, equity_before=agent['cash'],
                        stop=entry*.8, target=entry*1.4)
                    agent['cash'] -= premium+cost
                    liquidation = float(quote['bid'])*(1-policy['slippage_pct']/100)*quantity
                    agent['equity'] = agent['cash']+liquidation-fee(liquidation,policy)
                    agent['daily_entries'] += 1
                    event(agent,at,'entry','Simulated buy at next observed ask + slippage')
                else:
                    event(agent,at,'skip','Whole lot exceeds premium/cash budget or daily loss limit')
            else:
                event(agent,at,'skip','Signal cancelled: missing, delayed or unusable next quote')
        # Do not create another signal on a quote used for an exit or entry.
        else:
            if not allow_entries or stale or inconsistent:
                event(agent,at,'skip','Entries paused or source observations are stale/inconsistent')
            elif agent['equity'] <= agent['daily_start']-policy['daily_loss'] or agent['daily_entries'] >= policy['max_trades_per_day']:
                event(agent,at,'risk','Daily entry/loss limit reached')
            elif 585 < minute < 855:
                signal_history = [h for h in state['history'] if not fast or
                                  int(timestamp(h['at']).timestamp()) // 900 < int(now.timestamp()) // 900]
                side = direction(name,signal_history,spot)
                candidates = [r for r in quotes.values() if r['option_type']==side
                              and 2 <= (datetime.fromisoformat(r['expiry']).date()-local.date()).days <= 14]
                if candidates:
                    contract = min(candidates,key=lambda r:(r['expiry'],abs(r['strike']-spot)))
                    agent['pending'] = dict(signal_at=at,instrument_key=contract['instrument_key'],
                                            quote_at=contract.get('quote_at',at))
                    event(agent,at,'signal',f'{side} candidate; awaiting next recorded quote')
                else:
                    agent['status'] = 'Waiting for setup and liquid contract (2–14 days to expiry)'
        agent['peak'] = max(agent['peak'],agent['equity'])
        agent['max_drawdown'] = max(agent['max_drawdown'],agent['peak']-agent['equity'])
    # Strategy context stays on the 15-minute clock even with 1-second exits.
    # A mid-window start cannot manufacture a missing boundary observation.
    bucket = int(now.timestamp()) // 900
    if not fast or (int(now.timestamp()) % 900 <= 30 and
        (not state['history'] or int(timestamp(state['history'][-1]['at']).timestamp()) // 900 != bucket)):
        state['history'].append(dict(at=at,minute=minute,spot=spot))
    state['history'] = state['history'][-30:]
    state['day'],state['last_at'] = day,at


def connection(path):
    db=sqlite3.connect(str(path),timeout=2)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA busy_timeout=2000')
    return db


def paths():
    from .upstox_live import LiveConfig
    source=LiveConfig.from_environment().database_path
    return source,source.parent/'nifty_paper_agents.sqlite3'


def database():
    _,path=paths()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=connection(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL, started_at TEXT NOT NULL, state TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS backtests (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, result TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS stream_status (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS second_frames (at TEXT PRIMARY KEY, payload BLOB NOT NULL)')
    db.commit()
    return db


def read_quotes(start,end,after=None):
    source,_=paths()
    if not source.exists():
        return []
    with closing(sqlite3.connect(f'file:{source.resolve()}?mode=ro',uri=True,timeout=2)) as db:
        db.row_factory=sqlite3.Row
        rows=db.execute('''SELECT captured_at,underlying_key,provider,spot,expiry,instrument_key,
                option_type,strike,lot_size,bid,ask,volume,oi FROM option_snapshots
                WHERE local_date BETWEEN ? AND ? AND underlying_key='NSE_INDEX|Nifty 50'
                AND captured_at > ? ORDER BY captured_at,instrument_key LIMIT 250001''',
                (start,end,after or '')).fetchall()
    if len(rows)>250000:
        raise ValueError('Too many quotes; choose a shorter replay window')
    return [dict(r) for r in rows]


def summary(state):
    result=json.loads(json.dumps(state))
    result.pop('history',None)
    spreads=result.pop('spreads',None)
    research=result.pop('research',None)
    if research:
        result['research']={k:v for k,v in research.items() if k not in ('agents','candles','minutes','minute','iv_history')}
        result['research']['completed_bars']=len(research['candles'])
        result['research']['iv_days']=len(research['iv_history'])
        result['agents'].update(research['agents'])
    if spreads:
        result['agents'].update(spreads['agents'])
        result['candle_status']=dict(completed_1m=len(spreads['minutes']),completed_5m=len(spreads['candles']),required_5m=12)
    for name,agent in result['agents'].items():
        agent.setdefault('fee_model','Legacy illustrative costs')
        pnl=[t['pnl'] for t in agent['trades']]
        gains=sum(max(0,x) for x in pnl);losses=-sum(min(0,x) for x in pnl)
        agent['average_pnl']=round(sum(pnl)/len(pnl),2) if pnl else None
        agent['profit_factor']=round(gains/losses,2) if losses else None
        agent['total_charges']=round(sum(t.get('entry_cost',0)+t.get('exit_cost',0) for t in agent['trades']),2)
        agent['available_after_reserve']=round(agent['cash']-agent.get('capital_reserved',0),2)

    for agent in result['agents'].values():
        closed=agent['trades']
        agent['closed_trades']=len(closed)
        agent['net_pnl']=round(sum(t['pnl'] for t in closed),2)
        agent['win_rate']=round(100*sum(t['pnl']>0 for t in closed)/len(closed),1) if closed else None
        agent['equity']=round(agent['equity'],2)
        agent['cash']=round(agent['cash'],2)
        agent['max_drawdown']=round(agent['max_drawdown'],2)
        agent['trades']=closed[-100:]
        agent['events']=agent['events'][-30:]
    return result


def control(action):
    if action not in ('start','pause'):
        raise ValueError('Only start and pause are supported; paper accounts cannot be silently reset')
    with closing(database()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM sessions WHERE id=1').fetchone()
        if not row:
            if action=='start':
                db.execute('INSERT INTO sessions VALUES(1,1,?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps(fresh_state())))
        else:
            state=json.loads(row['state'])
            if action=='pause':
                for agent in [*state['agents'].values(),*state.get('spreads',{}).get('agents',{}).values(),*state.get('research',{}).get('agents',{}).values()]:
                    agent['pending']=None
            db.execute('UPDATE sessions SET enabled=?,state=? WHERE id=1',(int(action=='start'),json.dumps(state)))
    return dashboard()



def recover_legacy_position(strategy, expected_entry_at):
    """Explicit operator recovery of a halted PAPER position, never a gap fill.

    Liquidate at the latest fresh recorded bid with existing slippage/costs.
    The entry identity prevents an operator retry from closing a newer position.
    Normal streaming/replay never invokes this operation automatically.
    """
    if strategy not in STRATEGIES:
        raise ValueError('Recovery supports only the two legacy paper agents')
    with closing(database()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT state FROM sessions WHERE id=1').fetchone()
        if not row:
            raise ValueError('No paper session')
        state = json.loads(row['state'])
        agent = state['agents'][strategy]
        pos = agent['position']
        if not agent['blocked'] or not pos or pos.get('entry_at') != expected_entry_at:
            raise ValueError('Expected halted position no longer present; nothing changed')
        now = datetime.now(timezone.utc)
        local = now.astimezone(IST)
        if local.weekday() >= 5 or not 555 <= local.hour*60+local.minute < 930:
            raise ValueError('Recovery requires a live market-session quote')
        frame = db.execute('SELECT at,payload FROM second_frames ORDER BY at DESC LIMIT 1').fetchone()
        if not frame or not 0 <= (now-timestamp(frame['at'])).total_seconds() <= 5:
            raise ValueError('No fresh recorded frame; position remains unresolved')
        rows = json.loads(zlib.decompress(frame['payload']))
        quote = next((q for q in rows if q.get('instrument_key') == pos['instrument_key']), None)
        if (not quote or quote.get('provider') != 'upstox'
                or quote.get('underlying_key') != 'NSE_INDEX|Nifty 50'
                or quote.get('captured_at') != frame['at'] or not valid_quote(quote)
                or not quote.get('quote_at')
                or not 0 <= (now-timestamp(quote['quote_at'])).total_seconds() <= 5
                or timestamp(quote['quote_at']) <= timestamp(pos['entry_at'])
                or quote.get('expiry') != pos['expiry']
                or quote.get('option_type') != pos['option_type']
                or number(quote.get('strike')) != number(pos['strike'])
                or datetime.fromisoformat(pos['expiry']).date() < local.date()
                or (number(quote.get('bid_size')) or 0) < pos['quantity']):
            raise ValueError('Held contract lacks a fresh executable bid; position remains unresolved')
        policy = state['policy']
        exit_price = float(quote['bid']) * (1-policy['slippage_pct']/100)
        proceeds = exit_price * pos['quantity']
        exit_cost = fee(proceeds, policy)
        equity = agent['cash'] + proceeds - exit_cost
        reason = 'Operator recovery after data gap — current bid; missing-period exits unknown'
        trade = dict(**pos, exit_at=frame['at'], exit_price=round(exit_price,4),
                     exit_cost=round(exit_cost,2), pnl=round(equity-pos['equity_before'],2),
                     reason=reason, evidence_status='data_gap_recovery',
                     recovery_at=now.isoformat(), recovery_quote_at=quote['quote_at'],
                     recovery_bid=float(quote['bid']), recovery_bid_size=float(quote['bid_size']))
        agent['trades'].append(trade)
        agent.update(cash=equity, equity=equity, position=None, pending=None, blocked=False)
        agent['peak'] = max(agent['peak'], equity)
        agent['max_drawdown'] = max(agent['max_drawdown'], agent['peak']-equity)
        event(agent, now.isoformat(), 'recovery', reason)
        # Keep daily risk counters/history intact; recovery grants no fresh budget.
        db.execute('UPDATE sessions SET state=? WHERE id=1', (json.dumps(state),))
    return trade


def tick():
    """Called after existing collection; paused agents still monitor open exits."""
    if stream_enabled():
        return  # The streaming worker exclusively owns forward transitions.
    with closing(database()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM sessions WHERE id=1').fetchone()
        if not row:
            return
        state=json.loads(row['state'])
        now=datetime.now(timezone.utc)
        # Source rows are not backfilled into the live account. An interrupted
        # session's missing exit stays unresolved rather than inventing a fill.
        after=max(row['started_at'],state['last_at'] or row['started_at'])
        rows=read_quotes(now.astimezone(IST).date().isoformat(),now.astimezone(IST).date().isoformat(),after)
        for _,group in groupby(rows,key=lambda r:r['captured_at']):
            step(state,list(group),wall_now=now,allow_entries=bool(row['enabled']))
        db.execute('UPDATE sessions SET state=? WHERE id=1',(json.dumps(state),))


def backtest(start,end):
    first=datetime.strptime(start,'%Y-%m-%d').date()
    last=datetime.strptime(end,'%Y-%m-%d').date()
    if first>last or (last-first).days>60 or last>datetime.now(IST).date():
        raise ValueError('Choose a past range of at most 60 days')
    rows=read_quotes(start,end)
    state=fresh_state()
    batches=0
    sampled=0
    for _,group in groupby(rows,key=lambda r:r['captured_at']):
        previous=state['last_at']
        step(state,list(group))
        sampled+=int(state['last_at'] != previous)
        batches+=1
    result=dict(ok=True,mode='historical_replay',start=start,end=end,
        quote_rows=len(rows),observations=batches,sampled_observations=sampled,days=len({r['captured_at'][:10] for r in rows}),
        first_observation=rows[0]['captured_at'] if rows else None,last_observation=rows[-1]['captured_at'] if rows else None,
        status='research_only' if rows else 'no_data',**summary(state))
    with closing(database()) as db,db:
        db.execute('INSERT INTO backtests(created_at,result) VALUES(?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps(result)))
    return result


def dashboard():
    with closing(database()) as db:
        row=db.execute('SELECT * FROM sessions WHERE id=1').fetchone()
        latest=db.execute('SELECT created_at,result FROM backtests ORDER BY id DESC LIMIT 1').fetchone()
        stream=db.execute('SELECT payload FROM stream_status WHERE id=1').fetchone()
        from .replay import latest_job
        replay_job=latest_job(db)
        from .news_monitor import dashboard as news_dashboard
        news=news_dashboard(db,datetime.now(timezone.utc))
        db.commit()
    state=json.loads(row['state']) if row else fresh_state()
    from . import regime_agents
    state.setdefault('research',regime_agents.fresh())
    last=state['last_at']
    return dict(ok=True,mode='paper_only',enabled=bool(row and row['enabled']),
        interval_seconds=1 if stream_enabled() else 900,
        stream=json.loads(stream['payload']) if stream else None,
        started_at=row['started_at'] if row else None,
        quote_age_seconds=round((datetime.now(timezone.utc)-timestamp(last)).total_seconds()) if last else None,
        live=summary(state),news=news,replay_job=replay_job,last_backtest=json.loads(latest['result']) if latest else None)


def stream_enabled():
    return os.getenv('NIFTY_PAPER_STREAM_ENABLED', '').lower() in ('true', '1', 'yes')


def stream_tick(rows, status, *, now, prune=False):
    """Persist one-second evidence and account transition atomically. Never orders.

    Missing input cancels pending signals and freezes any open position as
    unresolved. A subsequent fresh quote cannot silently invent a gap fill.
    """
    at = now.astimezone(timezone.utc).isoformat()
    with closing(database()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR REPLACE INTO stream_status VALUES(1,?)', (json.dumps(status),))
        if rows:
            db.execute('INSERT OR IGNORE INTO second_frames VALUES(?,?)',
                (at, zlib.compress(json.dumps(rows,separators=(',',':')).encode(),1)))
        if prune:
            db.execute('DELETE FROM second_frames WHERE at < ?', ((now-timedelta(days=14)).isoformat(),))
        row = db.execute('SELECT * FROM sessions WHERE id=1').fetchone()
        if not row:
            return
        state = json.loads(row['state'])
        if state.get('version') != 'nifty-paper-v2-1s':
            state.update(version='nifty-paper-v2-1s', history=[], last_at=None, upgraded_at=at)
            for agent in state['agents'].values():
                agent['pending'] = None
                if agent['position']:
                    agent['blocked'] = True
                    event(agent,at,'migration','Existing position preserved unresolved on sampling change')
        from . import spread_agents, regime_agents, news_monitor
        news_before=news_monitor.capture(state)
        state.setdefault('research',regime_agents.fresh())
        regime_agents.advance(state['research'],rows,now,bool(row['enabled']))
        rows=[r for r in rows if r.get('option_type') in ('CE','PE')]
        if 'spreads' not in state:
            state['spreads']=spread_agents.fresh()
        spread_agents.advance(state['spreads'],rows,now,bool(row['enabled']))
        if not rows:
            for agent in state['agents'].values():
                agent['pending'] = None
                if agent['position'] and not agent['blocked']:
                    agent['blocked'] = True
                    event(agent,at,'data_gap','Live feed unavailable/stale; open position unresolved; agent halted')
                elif not agent['blocked']:
                    agent['status'] = status.get('status','Waiting for stream')
        else:
            step(state, rows, wall_now=now, allow_entries=bool(row['enabled']), interval_seconds=1)
        # Observer failures must not interrupt price evaluation or position exits.
        try:
            news_monitor.observe(db,state,news_before,now)
        except (ValueError,KeyError,TypeError,sqlite3.Error):
            pass
        db.execute('UPDATE sessions SET state=? WHERE id=1',(json.dumps(state),))


def pinned_contracts():
    with closing(database()) as db:
        row = db.execute('SELECT state FROM sessions WHERE id=1').fetchone()
    if not row:
        return set()
    state=json.loads(row['state'])
    keys={item['instrument_key'] for agent in state['agents'].values()
          for item in (agent['position'],agent['pending']) if item}
    keys.update(leg['instrument_key'] for agent in state.get('spreads',{}).get('agents',{}).values()
                for item in (agent['position'],agent['pending']) if item for leg in item['legs'])
    keys.update(leg['instrument_key'] for agent in state.get('research',{}).get('agents',{}).values()
                for item in (agent['position'],agent['pending']) if item for leg in item['legs'])
    return keys


def set_research_calendar(payload):
    from . import regime_agents
    config=regime_agents.calendar(payload)
    with closing(database()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM sessions WHERE id=1').fetchone()
        if not row:
            state=fresh_state()
            state['research']=regime_agents.fresh()
            db.execute('INSERT INTO sessions VALUES(1,0,?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps(state)))
        else:state=json.loads(row['state'])
        from .replay import schema
        schema(db)
        db.execute('INSERT INTO paper_calendar_reviews(reviewed_at,payload) VALUES(?,?)', (timestamp(config['reviewed_at']).astimezone(timezone.utc).isoformat(),json.dumps(config)))
        state.setdefault('research',regime_agents.fresh())['calendar']=config
        for a in state['research']['agents'].values():a['pending']=None
        db.execute('UPDATE sessions SET state=? WHERE id=1',(json.dumps(state),))
    return dashboard()
