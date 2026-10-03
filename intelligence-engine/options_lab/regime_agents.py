"""Versioned forward research suite. Shared paper ledger; no broker orders.

The four older experiments remain untouched. All decisions use completed bars;
execution requires a later fresh basket. Unknown event coverage fails closed.
"""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from . import paper_agents as p, spread_agents as s
from .iv_history import prior_observations

VERSION = 'nifty-regime-research-v1'
NAMES = ('regime_debit', 'regime_credit', 'iron_condor', 'long_straddle',
         'long_strangle', 'iron_fly', 'futures_trend')
POLICY = dict(capital=100000., trade_risk=2000., open_risk=4000., daily_loss=3000.,
              max_positions=2, max_entries=4, agent_entries=2)


def fresh():
    agents = s.fresh()['agents']
    prototype = agents['trend_pullback']
    import copy
    result = {name: copy.deepcopy(prototype) for name in NAMES}
    for a in result.values():
        a.update(cash=0., equity=0., daily_start=0., peak=0.,
                 status='Waiting for complete bars and a reviewed event calendar', shared_account=True)
    return dict(version=VERSION, agents=result, policy=dict(POLICY), last_at=None, day=None,
                minute=None, minutes=[], candles=[], last_bar=None, session_bars=0,
                iv_history=[], iv_today=None, iv_unit_version=1, regime=dict(name='WARMUP'),
                calendar=dict(date=None, windows=[]), daily_start=100000., peak=100000.,
                max_drawdown=0., halted=False, equity=100000., reserve=0., risk=0.,
                evidence_frames=0, first_observation=None)


def calendar(payload):
    """Explicit dated admin review. Times include timezone; limited to that day."""
    day = str(payload.get('date', ''))
    try:
        datetime.strptime(day, '%Y-%m-%d')
        if day < datetime.now(p.IST).date().isoformat():
            raise ValueError()
        windows = payload.get('windows', [])
        if not isinstance(windows, list) or len(windows)>20:
            raise ValueError()
        clean = []
        for w in windows:
            start, end = p.timestamp(w['start']), p.timestamp(w['end'])
            if start>=end or any(t.astimezone(p.IST).date().isoformat()!=day for t in (start,end)):
                raise ValueError()
            clean.append(dict(start=start.isoformat(), end=end.isoformat()))
        return dict(date=day, windows=clean, reviewed_at=datetime.now(p.IST).isoformat())
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError('Use today or a future date and up to 20 valid start/end windows on that date, with timezone')


def event_state(config, now):
    if config.get('date') != now.astimezone(p.IST).date().isoformat():
        return 'UNREVIEWED'
    if any(p.timestamp(w['start'])<=now<=p.timestamp(w['end']) for w in config['windows']):
        return 'BLACKOUT'
    return 'POST_EVENT' if any(0<(now-p.timestamp(w['end'])).total_seconds()<=3600 for w in config['windows']) else 'CLEAR'


def ema(values, length):
    value = sum(values[:length])/length
    for x in values[length:]:
        value += 2/(length+1)*(x-value)
    return value


def indicators(bars):
    if len(bars)<50:
        return None
    tr=[];plus=[];minus=[]
    for prev,cur in zip(bars,bars[1:]):
        tr.append(max(cur['high']-cur['low'],abs(cur['high']-prev['close']),abs(cur['low']-prev['close'])))
        up=cur['high']-prev['high'];down=prev['low']-cur['low']
        plus.append(max(up,0) if up>down else 0);minus.append(max(down,0) if down>up else 0)
    atr=sum(tr[:14])/14;pos=sum(plus[:14])/14;neg=sum(minus[:14])/14;dx=[]
    for i in range(13,len(tr)):
        if i>13:
            atr=(atr*13+tr[i])/14;pos=(pos*13+plus[i])/14;neg=(neg*13+minus[i])/14
        dx.append(100*abs(pos-neg)/(pos+neg) if pos+neg else 0.)
    adx=sum(dx[:14])/14
    for d in dx[14:]:adx=(adx*13+d)/14
    closes=[b['close'] for b in bars]
    returns=[math.log(b/a) for a,b in zip(closes[-21:-1],closes[-20:])]
    avg=sum(returns)/len(returns)
    rv=(math.sqrt(sum((r-avg)**2 for r in returns)/(len(returns)-1)*75*252)*100
        if all(b['at']-a['at']==300 for a,b in zip(bars[-21:-1],bars[-20:])) else None)
    return dict(ema20=ema(closes,20),ema50=ema(closes,50),adx=adx,atr=atr,rv=rv)


def context(state, rows, now):
    bars=state['candles'];ind=indicators(bars);event=event_state(state['calendar'],now)
    result=dict(name='WARMUP',event=event,bars=len(bars),session_bars=state['session_bars'],
                iv_days=len(state['iv_history']),iv_percentile=None,iv=None,**(ind or {}))
    spot=bars[-1]['close'] if bars else next((r.get('spot') for r in rows if r.get('spot')),None)
    if spot is None:return result
    options=[r for r in rows if r['option_type'] in ('CE','PE')]
    expiries=sorted({r['expiry'] for r in options})
    ivs=[]
    if expiries:
        for side in ('CE','PE'):
            chain=[r for r in options if r['expiry']==expiries[0] and r['option_type']==side]
            if chain:
                iv=p.number(min(chain,key=lambda r:abs(r['strike']-spot)).get('iv'))
                if iv and 0<iv<200:ivs.append(iv)
    iv=sum(ivs)/2 if len(ivs)==2 else None
    prior=prior_observations(state['iv_history'],now)
    history=[x['iv'] for x in prior]
    recent=bool(prior and (now.astimezone(p.IST).date()-datetime.fromisoformat(prior[-1]['day']).date()).days<=10)
    result.update(iv_days=len(prior),iv_history_last_day=prior[-1]['day'] if prior else None,iv_history_fresh=recent)
    percentile=100*sum(v<iv for v in history)/len(history) if iv and len(history)>=20 and recent else None
    result.update(iv=iv,iv_percentile=percentile)
    if event in ('UNREVIEWED','BLACKOUT'):
        result['name']='EVENT_RISK';return result
    if not ind or state['session_bars']<3:return result
    # IV percentile is a rolling near-expiry proxy; tenor changes are disclosed.
    prior=bars[-7:-1];upper=max(b['high'] for b in prior);lower=min(b['low'] for b in prior)
    compressed=state['session_bars']>=7 and upper-lower<3*ind['atr']
    if compressed and (spot>upper or spot<lower):
        result['name']='VOL_BREAKOUT'
    elif ind['adx']>=25 and ind['ema20']>ind['ema50'] and spot>ind['ema20']:
        result['name']='TREND_UP'
    elif ind['adx']>=25 and ind['ema20']<ind['ema50'] and spot<ind['ema20']:
        result['name']='TREND_DOWN'
    elif ind['adx']<18 and percentile is not None and percentile>=60:
        result['name']='RANGE_HIGH_IV'
    else:result['name']='NO_TRADE'
    return result


def eligible(row, now):
    if row.get('option_type')!='FUT':return s.usable(row,now)
    try:
        return (row.get('provider')=='upstox' and row.get('underlying_key')=='NSE_INDEX|Nifty 50'
                and p.valid_quote(row) and (float(row['ask'])-float(row['bid']))/float(row['ask'])<=.001
                and 0<=(now-p.timestamp(row['quote_at'])).total_seconds()<=5
                and min(float(row['bid_size']),float(row['ask_size']))>=row['lot_size']
                and datetime.fromisoformat(row['expiry']).date()>now.astimezone(p.IST).date())
    except (ValueError,TypeError,KeyError):return False


def choose(name, ctx, rows, spot, bars):
    regime=ctx['name'];up=regime=='TREND_UP';side='CE' if up else 'PE'
    trend=regime in ('TREND_UP','TREND_DOWN')
    if name in ('regime_debit','regime_credit','futures_trend') and not trend:return None,'Needs a confirmed trend'
    if name=='futures_trend':
        futures=sorted((r for r in rows if r['option_type']=='FUT'),key=lambda r:r['expiry'])
        for r in futures[:1]:
            vwap=p.number(r.get('vwap'));ltp=p.number(r.get('ltp'))
            if vwap and ltp and ((ltp>vwap)==up):return [dict(**r,side='BUY' if up else 'SELL')],'Futures trend and own-contract VWAP'
        return None,'Needs a fresh NIFTY futures quote and its exchange average traded price'
    if name=='regime_debit':
        prev,last=bars[-2:]
        level=ema([b['close'] for b in bars[:-1]],20)
        if not (prev['low']<=level and last['close']>prev['high'] if up else prev['high']>=level and last['close']<prev['low']):
            return None,'Waiting for completed pullback confirmation'
        return s.select_legs(rows,dict(side=side),'trend_pullback',spot),'Trend pullback'
    if name in ('regime_credit','iron_condor','iron_fly'):
        if ctx.get('iv_percentile') is None:return None,'Needs 20 prior daily ATM-IV observations'
        if ctx['iv_percentile']<60:return None,'IV percentile below 60'
    if name in ('iron_condor','iron_fly') and regime!='RANGE_HIGH_IV':return None,'Needs range / high-IV regime'
    if name=='iron_fly' and ctx['event']!='POST_EVENT':return None,'Needs a reviewed blackout that ended within 60 minutes'
    if name in ('long_straddle','long_strangle'):
        if regime!='VOL_BREAKOUT':return None,'Needs compression followed by a completed breakout'
        if ctx.get('iv_percentile') is None:return None,'Needs 20 prior daily ATM-IV observations'
        if ctx['iv_percentile']>40:return None,'Long-volatility entry requires IV percentile at or below 40'
    options=[r for r in rows if r['option_type'] in ('CE','PE')]
    for expiry in sorted({r['expiry'] for r in options}):
        chain=[r for r in options if r['expiry']==expiry]
        # Treat each lot size as its own basket universe.
        for lot in sorted({r['lot_size'] for r in chain}):
            c=[r for r in chain if r['lot_size']==lot]
            def atm(kind):
                items=[r for r in c if r['option_type']==kind]
                return min(items,key=lambda r:abs(r['strike']-spot)) if items else None
            def delta(kind):
                items=[r for r in c if r['option_type']==kind and (r['strike']-spot)*(1 if kind=='CE' else -1)>0
                       and p.number(r.get('greeks',{}).get('delta')) is not None
                       and .15<=abs(float(r['greeks']['delta']))<=.20]
                return min(items,key=lambda r:abs(abs(float(r['greeks']['delta']))-.175)) if items else None
            def wing(short):
                items=[r for r in c if r['option_type']==short['option_type']
                       and 50<=(r['strike']-short['strike'])*(1 if r['option_type']=='CE' else -1)<=300]
                return min(items,key=lambda r:abs(r['strike']-short['strike'])) if items else None
            if name in ('long_straddle','long_strangle'):
                call,put=(atm('CE'),atm('PE')) if name=='long_straddle' else (delta('CE'),delta('PE'))
                if call and put and (name!='long_straddle' or call['strike']==put['strike']):
                    return [dict(**call,side='BUY'),dict(**put,side='BUY')],'Long volatility'
            else:
                kinds=[('PE' if up else 'CE')] if name=='regime_credit' else ['PE','CE']
                shorts=[atm(k) if name=='iron_fly' else delta(k) for k in kinds]
                if any(r is None for r in shorts):continue
                if name=='iron_fly' and shorts[0]['strike']!=shorts[1]['strike']:continue
                longs=[wing(r) for r in shorts]
                if all(longs):
                    return [dict(**r,side='BUY') for r in longs]+[dict(**r,side='SELL') for r in shorts],'Hedged credit basket'
    return None,'No same-expiry whole-lot basket with eligible strikes / deltas'


def charges(notional, side, future=False):
    if not future:return s.costs(notional,side)
    c=dict(brokerage=min(20.,notional*.0005),stt=notional*.0005 if side=='SELL' else 0.,
           exchange=notional*.0000183,sebi=notional*.000001,ipft=0.,
           stamp=notional*.00002 if side=='BUY' else 0.)
    c['gst']=.18*(c['brokerage']+c['exchange']+c['ipft']);c['total']=sum(c.values());return c


def execute(legs, quotes, now, entry, signal_at=None):
    fills=[];times=[]
    for leg in legs:
        q=quotes.get(leg['instrument_key'])
        if not q or not eligible(q,now) or any(q[k]!=leg[k] for k in ('option_type','strike','expiry','lot_size')):return None
        qt=p.timestamp(q['quote_at'])
        if signal_at and qt<=p.timestamp(signal_at):return None
        times.append(qt.timestamp());side=leg['side'] if entry else ('SELL' if leg['side']=='BUY' else 'BUY')
        future=q['option_type']=='FUT';slip=.0002 if future else .005
        price=float(q['ask'])*(1+slip) if side=='BUY' else float(q['bid'])*(1-slip)
        fills.append(dict(instrument_key=q['instrument_key'],option_type=q['option_type'],strike=q['strike'],
                          expiry=q['expiry'],lot_size=q['lot_size'],side=side,price=price,quote_at=q['quote_at'],
                          charges=charges(price*q['lot_size'],side,future)))
    return fills if fills and max(times)-min(times)<=1 else None


def terms(fills, ctx):
    if not fills:return None
    entry_cost=sum(f['charges']['total'] for f in fills);q=fills[0]['lot_size']
    if any(f['lot_size']!=q or f['expiry']!=fills[0]['expiry'] for f in fills):return None
    if fills[0]['option_type']=='FUT':
        # Full notional reserve avoids pretending an estimated margin is SPAN.
        risk=max(2*ctx['atr']*q,500)+entry_cost
        return dict(max_loss=None,planned_risk=risk,stop_loss=risk,target_profit=2*risk,
                    max_profit=None,reserve=fills[0]['price']*q,entry_cost=entry_cost,quantity=q)
    net=sum((1 if f['side']=='SELL' else -1)*f['price']*q for f in fills)
    def payoff(x):
        return net+sum((1 if f['side']=='BUY' else -1)*q*max(0,(x-f['strike'])*(1 if f['option_type']=='CE' else -1)) for f in fills)
    slope=sum((1 if f['side']=='BUY' else -1)*q for f in fills if f['option_type']=='CE')
    if slope<0:return None  # Unlimited upside loss is never eligible.
    points=[0]+[f['strike'] for f in fills];values=[payoff(x) for x in points]
    risk=max(0,-min(values))+entry_cost
    reward=None if slope>0 else max(values)-entry_cost
    if risk<=0 or (reward is not None and reward<=2*entry_cost):return None
    is_long=all(f['side']=='BUY' for f in fills)
    return dict(max_loss=risk,planned_risk=risk,stop_loss=.35*risk,
                target_profit=.5*risk if is_long else .5*reward,max_profit=reward,
                reserve=risk,entry_cost=entry_cost,quantity=q)


def mark(a, fills):
    pos=a['position']
    if pos['legs'][0]['option_type']=='FUT':
        entry=pos['legs'][0];exit=fills[0]
        return a['cash']+(exit['price']-entry['price'])*entry['lot_size']*(1 if entry['side']=='BUY' else -1)-exit['charges']['total']
    return a['cash']+s.cashflow(fills)


def totals(state):
    agents=state['agents'].values();positions=[a['position'] for a in agents if a['position']]
    state.update(equity=POLICY['capital']+sum(a['equity'] for a in state['agents'].values()),
                 reserve=sum(x['reserve'] for x in positions),risk=sum(x['planned_risk'] for x in positions))
    state['peak']=max(state['peak'],state['equity'])
    state['max_drawdown']=max(state['max_drawdown'],state['peak']-state['equity'])


def admission(state, name, t, legs):
    positions=[a['position'] for a in state['agents'].values() if a['position']]
    if state['halted'] or any(a['blocked'] for a in state['agents'].values()):return 'Shared account halted or unresolved'
    if state['equity']<=state['daily_start']-POLICY['daily_loss']:return 'Shared daily loss limit'
    if t['planned_risk']>POLICY['trade_risk'] or state['risk']+t['planned_risk']>POLICY['open_risk']:return 'Shared planned-risk budget exceeded'
    if state['reserve']+t['reserve']>state['equity']:return 'Insufficient shared paper reserve (futures require full notional)'
    if len(positions)>=POLICY['max_positions']:return 'Shared position limit'
    if sum(a['daily_entries'] for a in state['agents'].values())>=POLICY['max_entries']:return 'Shared daily entry limit'
    if state['agents'][name]['daily_entries']>=POLICY['agent_entries']:return 'Strategy daily entry limit'
    held={l['instrument_key'] for pos in positions for l in pos['legs']}
    if any(l['instrument_key'] in held for l in legs):return 'Overlapping contract already held by another strategy'
    return None


def advance(state, rows, now, allow_entries):
    at=now.isoformat();local=now.astimezone(p.IST);day=local.date().isoformat();minute=local.hour*60+local.minute
    if state['last_at'] and int(now.timestamp())<=int(p.timestamp(state['last_at']).timestamp()):return
    gap=bool(state['last_at'] and (now-p.timestamp(state['last_at'])).total_seconds()>5)
    newday=state['day']!=day;active=local.weekday()<5 and 555<=minute<930
    quotes={r['instrument_key']:r for r in rows if eligible(r,now)}
    spots=[]
    for r in quotes.values():
        try:
            if 0<=(now-p.timestamp(r['spot_at'])).total_seconds()<=5 and p.number(r['spot']) and r['spot']>0:spots.append(r['spot'])
        except (KeyError,ValueError,TypeError):pass
    valid=active and bool(spots) and (max(spots)-min(spots))/min(spots)<.002
    if newday:
        if state['iv_today']:
            state['iv_history']=prior_observations([state['iv_today']]+state['iv_history'],now)
        state.update(iv_today=None,daily_start=state['equity'],halted=any(a['blocked'] for a in state['agents'].values()))
        for a in state['agents'].values():a.update(daily_entries=0,pending=None)
    if newday or gap or not valid:
        # Keep completed historical bars across sessions, discard partial bars.
        state.update(minute=None,minutes=[],session_bars=0)
    completed=None
    if valid:
        # Reuse strict OHLC sampling while preserving up to 100 completed bars.
        history=list(state['candles']);completed=s.candle_sample(state,now,spots[0])
        state['candles']=(history+[completed])[-100:] if completed else history
        if completed:state['session_bars']+=1
        state['evidence_frames']+=1;state['first_observation']=state['first_observation'] or at
    if completed or newday or not valid or state.pop('iv_recompute',False) or not state['regime'].get('iv'):
        state['regime']=context(state,list(quotes.values()),now)
    # Event gates are evaluated each second even between bar boundaries.
    event=event_state(state['calendar'],now)
    ctx=dict(state['regime'],event=event)
    if event in ('UNREVIEWED','BLACKOUT'):ctx['name']='EVENT_RISK'
    state['regime']=ctx
    if completed and ctx.get('iv'):
        state['iv_today']=dict(day=day,iv=ctx['iv'],at=at,available_at=at,unit='percent',source='Upstox V3 stream',method='last-completed-bar-atm-ce-pe-v1')
    # Exit/mark every open basket before admitting any new exposure.
    for name,a in state['agents'].items():
        pos=a['position']
        if not pos:continue
        if a['blocked']:continue
        fills=execute(pos['legs'],quotes,now,False) if valid and not gap and not newday else None
        if not fills:
            a['blocked']=True;state['halted']=True;p.event(a,at,'data_gap','Unresolved basket: shared account halted; last mark retained');continue
        a['equity']=mark(a,fills)
    totals(state)
    if state['equity']<=state['daily_start']-POLICY['daily_loss']:state['halted']=True
    for name,a in state['agents'].items():
        pos=a['position']
        if a['blocked']:continue
        if pos:
            pnl=a['equity']-pos['equity_before']
            reason=('Session exit' if minute>=915 else 'Event / shared risk exit' if event in ('UNREVIEWED','BLACKOUT') or state['halted']
                    else 'Basket stop' if pnl<=-pos['stop_loss'] else 'Basket target' if pnl>=pos['target_profit']
                    else 'Time stop' if (now-p.timestamp(pos['entry_at'])).total_seconds()>=pos['max_seconds'] else None)
            if reason:
                fills=execute(pos['legs'],quotes,now,False)
                a['cash']=a['equity'];a['position']=None;a['capital_reserved']=0.
                a['trades'].append(dict(**pos,exit_at=at,exit_legs=fills,pnl=round(pnl,2),reason=reason,exit_cost=sum(f['charges']['total'] for f in fills)))
                p.event(a,at,'exit',reason)
        a['peak']=max(a['peak'],a['equity']);a['max_drawdown']=max(a['max_drawdown'],a['peak']-a['equity'])
    totals(state)
    for name,a in state['agents'].items():
        if a['position'] or a['blocked']:continue
        pending=a['pending'];a['pending']=None
        if not allow_entries or not valid or state['halted'] or ctx['name']=='EVENT_RISK' or not 600<=minute<855:
            a['status']=('Shared account halted' if state['halted'] else 'New entries paused' if not allow_entries else
                         'Review today’s event calendar' if event=='UNREVIEWED' else 'Event blackout' if event=='BLACKOUT' else
                         'Waiting for market / fresh quotes' if not valid else 'Outside 10:00–14:15 entry window');continue
        if pending:
            fills=execute(pending['legs'],quotes,now,True,pending['signal_at']) if not gap and 0<(now-p.timestamp(pending['signal_at'])).total_seconds()<=5 else None
            t=terms(fills,pending['context']) if fills else None
            reason=admission(state,name,t,fills) if t else 'No eligible next-quote basket / payoff'
            if reason:p.event(a,at,'skip',reason);continue
            a['position']=dict(**t,legs=fills,entry_at=at,signal_at=pending['signal_at'],equity_before=a['cash'],
                               context=pending['context'],version=VERSION,max_seconds=1800 if name in ('long_straddle','long_strangle','iron_fly') else 7200)
            a['cash']+=-t['entry_cost'] if fills[0]['option_type']=='FUT' else s.cashflow(fills)
            a['capital_reserved']=t['reserve'];a['daily_entries']+=1
            a['equity']=mark(a,execute(fills,quotes,now,False));totals(state)
            p.event(a,at,'entry','All-or-none next-quote paper basket; shared budget reserved')
        elif completed:
            legs,reason=choose(name,ctx,list(quotes.values()),spots[0],state['candles']) if ctx['name']!='WARMUP' else (None,'Needs 50 complete bars and 3 fresh session bars')
            if legs:
                a['pending']=dict(legs=legs,signal_at=at,context=ctx);p.event(a,at,'signal',reason)
            else:a['status']=reason
    state['last_at']=at;state['day']=day
