"""Forward-only, defined-risk experiments. No broker orders.

Candles aggregate one-second spot observations, not complete exchange ticks.
Multi-leg fills are atomic paper assumptions; margin is a model reserve, not SPAN.
"""
from __future__ import annotations
import math
from datetime import datetime
from . import paper_agents as p

NAMES = ('trend_pullback', 'volatility_credit')
VERSION = 'nifty-spreads-v1'
FEE_MODEL = 'NSE-Upstox-2026-09-29-inclusive-IPFT'


def fresh():
    agents = {}
    for name in NAMES:
        agents[name] = dict(cash=100000., equity=100000., daily_start=100000.,
            daily_entries=0, position=None, pending=None, trades=[], events=[],
            blocked=False, peak=100000., max_drawdown=0., last_signal_bar=None,
            status='Warming up: 12 complete five-minute candles required',
            fee_model=FEE_MODEL, capital_reserved=0.)
    return dict(version=VERSION, agents=agents, last_at=None, day=None,
                minute=None, minutes=[], candles=[], last_bar=None)


def costs(notional, side):
    # https://upstox.com/brokerage-charges/; NSE STT effective 2026-04-01.
    # NSE transaction charge includes the former IPFT component from March 2026.
    charges = dict(brokerage=20., stt=notional*.0015 if side=='SELL' else 0.,
        exchange=notional*.0003553, sebi=notional*.000001,
        ipft=0., stamp=notional*.00003 if side=='BUY' else 0.)
    charges['gst'] = .18*(charges['brokerage']+charges['exchange']+charges['ipft'])
    charges['total'] = sum(charges.values())
    return charges


def candle_sample(state, now, spot):
    """Close candles only after a boundary; discard incomplete minute groups."""
    second = int(now.timestamp())
    bucket = second//60*60
    current = state['minute']
    completed = None
    if current and current['at'] != bucket:
        good = current['first'] <= current['at']+2 and current['last'] >= current['at']+57 and current['count']>=55
        if good:
            state['minutes'].append(current)
            state['minutes'] = state['minutes'][-65:]
            group = [m for m in state['minutes'] if m['at']//300==current['at']//300]
            if current['at']%300==240 and len(group)==5 and group[-1]['at']-group[0]['at']==240:
                completed = dict(at=group[0]['at'],open=group[0]['open'],close=group[-1]['close'],
                    high=max(m['high'] for m in group),low=min(m['low'] for m in group))
                state['candles'].append(completed)
                state['candles'] = state['candles'][-30:]
                state['last_bar'] = completed['at']
        else:
            state['minutes']=[];state['candles']=[]
        current = None
    if not current:
        current=dict(at=bucket,first=second,last=second,count=1,open=spot,high=spot,low=spot,close=spot)
    elif second>current['last']:
        current.update(last=second,count=current['count']+1,high=max(spot,current['high']),low=min(spot,current['low']),close=spot)
    state['minute']=current
    return completed


def setup(candles, name):
    if len(candles)<12 or any(b['at']-a['at']!=300 for a,b in zip(candles[-12:-1],candles[-11:])):
        return None
    bars=candles[-12:]; closes=[c['close'] for c in bars]
    slow=sum(closes[-10:])/10; fast=sum(closes[-3:])/3
    slope=(closes[-1]/closes[-6]-1)
    side='CE' if fast>slow and slope>.001 else 'PE' if fast<slow and slope<-.001 else None
    if not side:return None
    if name=='trend_pullback':
        # Pullback on the previous completed bar, confirmation on the last bar.
        prior,last=bars[-2:]; level=sum(closes[-5:-2])/3
        if side=='CE' and not (prior['low']<=level and last['close']>prior['high']):return None
        if side=='PE' and not (prior['high']>=level and last['close']<prior['low']):return None
    else:
        # Avoid violently trending bars; credit setup is a moderate trend only.
        if abs(slope)>.006 or (bars[-1]['high']-bars[-1]['low'])/closes[-1]>.004:return None
    returns=[math.log(b/a) for a,b in zip(closes,closes[1:])]
    mean=sum(returns)/len(returns)
    rv=math.sqrt(sum((r-mean)**2 for r in returns)/(len(returns)-1)*75*252)*100
    return dict(side=side, rv=rv, bar_at=bars[-1]['at'])


def usable(row, now):
    try:
        return (row.get('provider')=='upstox' and row.get('underlying_key')=='NSE_INDEX|Nifty 50'
            and p.valid_quote(row) and row.get('quote_at')
            and 0 <= (now-p.timestamp(row['quote_at'])).total_seconds()<=5
            and min(p.number(row.get('bid_size')) or 0,p.number(row.get('ask_size')) or 0)>=row['lot_size']
            and 2 <= (datetime.fromisoformat(row['expiry']).date()-now.astimezone(p.IST).date()).days<=14)
    except (KeyError,ValueError,TypeError):return False


def select_legs(rows, signal, name, spot):
    side=signal['side'] if name=='trend_pullback' else ('PE' if signal['side']=='CE' else 'CE')
    candidates=[r for r in rows if r['option_type']==side]
    for expiry in sorted({r['expiry'] for r in candidates}):
        chain=sorted((r for r in candidates if r['expiry']==expiry),key=lambda r:r['strike'])
        if name=='trend_pullback':
            if not chain:continue
            long=min(chain,key=lambda r:abs(r['strike']-spot))
            shorts=[r for r in chain if (r['strike']-long['strike'])*(1 if side=='CE' else -1)>0
                    and 50<=abs(r['strike']-long['strike'])<=200 and r['lot_size']==long['lot_size']]
            if shorts:
                short=min(shorts,key=lambda r:abs(abs(r['strike']-long['strike'])-50))
                return [dict(**long,side='BUY'),dict(**short,side='SELL')]
        else:
            # Same-expiry ATM IV proxy versus intraday RV, not a calibrated forecast.
            if not chain:continue
            atm=min(chain,key=lambda r:abs(r['strike']-spot));iv=p.number(atm.get('iv'))
            if iv is None or not 0<iv<=200 or iv<max(12.,signal['rv']*1.25):continue
            shorts=[r for r in chain if (r['strike']-spot)*(1 if side=='CE' else -1)>spot*.003]
            for short in sorted(shorts,key=lambda r:abs(r['strike']-spot)):
                longs=[r for r in chain if (r['strike']-short['strike'])*(1 if side=='CE' else -1)>0
                       and 50<=abs(r['strike']-short['strike'])<=200 and r['lot_size']==short['lot_size']]
                if longs:
                    long=min(longs,key=lambda r:abs(abs(r['strike']-short['strike'])-50))
                    return [dict(**long,side='BUY'),dict(**short,side='SELL')]
    return None


def execution(legs, quotes, now, *, entry, signal_at=None):
    """All-or-none paper basket. Never fabricate a partial or naked position."""
    result=[];times=[]
    for leg in legs:
        q=quotes.get(leg['instrument_key'])
        if not q or not usable(q,now):return None
        if any(q[k]!=leg[k] for k in ('expiry','lot_size','strike','option_type')):return None
        qt=p.timestamp(q['quote_at']);times.append(qt.timestamp())
        if signal_at and qt<=p.timestamp(signal_at):return None
        side=leg['side'] if entry else ('SELL' if leg['side']=='BUY' else 'BUY')
        price=float(q['ask'])*1.005 if side=='BUY' else float(q['bid'])*.995
        charge=costs(price*leg['lot_size'],side)
        result.append(dict(instrument_key=leg['instrument_key'],option_type=leg['option_type'],strike=leg['strike'],
            expiry=leg['expiry'],lot_size=leg['lot_size'],side=side,price=price,quote_at=q['quote_at'],charges=charge))
    return result if max(times)-min(times)<=1 else None


def cashflow(fills):
    return sum((1 if f['side']=='SELL' else -1)*f['price']*f['lot_size']-f['charges']['total'] for f in fills)


def terms(fills,name,spot):
    long=next(f for f in fills if f['side']=='BUY');short=next(f for f in fills if f['side']=='SELL')
    quantity=long['lot_size'];width=abs(long['strike']-short['strike']);debit=long['price']-short['price']
    entry_cost=sum(f['charges']['total'] for f in fills)
    if name=='trend_pullback':
        if not 0<debit<width:return None
        risk=debit*quantity;reward=(width-debit)*quantity
        stop=risk*.4;target=reward*.5
    else:
        credit=-debit
        if not width*.15<=credit<=width*.6:return None
        risk=(width-credit)*quantity;reward=credit*quantity
        stop=min(risk*.5,reward);target=reward*.5
    # Fully collateralised paper reserve; NOT an exchange/broker margin quote.
    reserve=width*quantity+long['price']*quantity+entry_cost
    if risk+entry_cost>2000 or reward<2*entry_cost or reserve>100000:return None
    return dict(quantity=quantity,width=width,entry_price=debit,max_loss=risk+entry_cost,
                max_profit=reward-entry_cost,stop_loss=stop,target_profit=target,
                reserve=reserve,entry_cost=entry_cost,fee_model=FEE_MODEL)


def advance(state, rows, now, allow_entries):
    at=now.isoformat();local=now.astimezone(p.IST);day=local.date().isoformat();minute=local.hour*60+local.minute
    if state['last_at'] and int(now.timestamp())<=int(p.timestamp(state['last_at']).timestamp()):return
    active=local.weekday()<5 and 555<=minute<930
    gap=bool(state['last_at'] and (now-p.timestamp(state['last_at'])).total_seconds()>5)
    new_day=state['day']!=day
    quotes={r['instrument_key']:r for r in rows if usable(r,now)}
    spots=[p.number(r.get('spot')) for r in rows if r.get('spot_at') and 0<=(now-p.timestamp(r['spot_at'])).total_seconds()<=5]
    spots=[s for s in spots if s and s>0]
    valid=active and bool(quotes) and bool(spots) and (max(spots)-min(spots))/min(spots)<.002
    if new_day or gap or not valid:
        state.update(minute=None,minutes=[],candles=[],last_bar=None)
    completed=candle_sample(state,now,spots[0]) if valid else None
    for name,a in state['agents'].items():
        if new_day:
            a.update(daily_start=a['equity'],daily_entries=0,last_signal_bar=None,pending=None)
        pos=a['position']
        if pos and (gap or new_day or not valid):
            a['blocked']=True;a['pending']=None
            p.event(a,at,'data_gap','Spread unresolved across data gap; both legs preserved, agent halted')
        if a['blocked']:continue
        if pos:
            fills=execution(pos['legs'],quotes,now,entry=False)
            if not fills:
                a['blocked']=True;p.event(a,at,'data_gap','Both spread exit quotes unavailable or unsynchronised; agent halted');continue
            equity=a['cash']+cashflow(fills);pnl=equity-pos['equity_before'];a['equity']=equity
            reason=('Session exit' if minute>=915 else 'Daily loss limit' if equity<=a['daily_start']-2000
                    else 'Spread stop' if pnl<=-pos['stop_loss'] else 'Spread target' if pnl>=pos['target_profit'] else None)
            if reason:
                a['cash']=equity;a['capital_reserved']=0.;a['position']=None
                a['trades'].append(dict(**pos,exit_at=at,exit_legs=fills,pnl=round(pnl,2),reason=reason,
                    exit_cost=sum(f['charges']['total'] for f in fills)))
                p.event(a,at,'exit',reason)
        elif a['pending']:
            pending=a['pending'];a['pending']=None
            fills=execution(pending['legs'],quotes,now,entry=True,signal_at=pending['signal_at']) if valid and not gap and allow_entries and minute<855 else None
            t=terms(fills,name,spots[0]) if fills and (now-p.timestamp(pending['signal_at'])).total_seconds()<=5 else None
            if t and t['reserve']<=a['cash'] and a['daily_entries']<2 and a['equity']>a['daily_start']-2000:
                a['position']=dict(**t,legs=fills,entry_at=at,signal_at=pending['signal_at'],
                    equity_before=a['cash'],signal=pending['signal'],expiry=fills[0]['expiry'])
                a['cash']+=cashflow(fills);a['capital_reserved']=t['reserve'];a['daily_entries']+=1
                close=execution(fills,quotes,now,entry=False)
                a['equity']=a['cash']+cashflow(close)
                p.event(a,at,'entry','Both legs simulated at next fresh bid/ask with 0.5% adverse slippage')
            else:p.event(a,at,'skip','Basket cancelled: missing next quotes, cost/risk budget or reserve check failed')
        elif not valid:
            a['status']='Waiting for market / fresh quotes'
        elif not allow_entries:a['status']='New entries paused'
        elif a['daily_entries']>=2 or a['equity']<=a['daily_start']-2000:a['status']='Daily entry/loss limit reached'
        elif len(state['candles'])<12:a['status']=f"Warming up: {len(state['candles'])}/12 complete five-minute candles"
        elif not 615<=minute<855:a['status']='Outside 10:15–14:15 entry window'
        elif completed and a['last_signal_bar']!=completed['at']:
            a['last_signal_bar']=completed['at'];signal=setup(state['candles'],name)
            legs=select_legs(list(quotes.values()),signal,name,spots[0]) if signal else None
            if legs:
                a['pending']=dict(legs=legs,signal_at=at,signal=signal)
                p.event(a,at,'signal','Completed five-minute setup; waiting for newer quotes on both legs')
            else:a['status']='Waiting for trend, volatility filter and eligible spread'
        a['peak']=max(a['peak'],a['equity']);a['max_drawdown']=max(a['max_drawdown'],a['peak']-a['equity'])
    state['last_at']=at;state['day']=day
