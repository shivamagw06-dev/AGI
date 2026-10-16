"""Prospective news-gated NIFTY option experiment and identical price-only control.
No HTTP, LLM, credentials or broker-order code. State commits with stream evidence.
"""
from __future__ import annotations
import copy
import hashlib
import re
from datetime import datetime
from . import paper_agents as p, spread_agents as s, regime_agents as r

VERSION = 'nifty-news-reaction-v1'
POLICY = dict(capital=100000., max_premium=5000., daily_loss=2000., max_entries=2,
              stop_pct=.20, target_pct=.40, max_hold_seconds=1200, cooldown_seconds=600,
              publication_max_delay=300, event_lifetime=600, feed_max_age=180)
NAMES = ('news_reaction', 'price_control')
EXCLUDE = re.compile(r'\?|\b(expected|expects?|may|might|could|likely|preview|ahead of|yesterday|recap|roundup|stocks to watch|what to watch|rumou?r|not|denies?|denied|fake|false|reportedly|sources say|considers?|plans?|proposes?|would|should|warning|warns?|forecasts?|predicts?|last week|last month|last year)\b', re.I)
TOPICS = (
    ('India monetary policy', r'\b(rbi|reserve bank of india)\b.{0,100}\b(cuts?|raises?|hikes?|holds?|keeps?|reduces?|announces?)\b.{0,60}\b(repo|rates?|crr|slr|liquidity)\b'),
    ('India macro release', r'\b(india|indian)\b.{0,70}\b(cpi|inflation|gdp|industrial production)\b.{0,60}\b(rises?|falls?|slows?|accelerates?|prints?|released|grew|grows?|contracts?)\b'),
    ('US monetary policy', r'\b(fed|federal reserve|fomc)\b.{0,70}\b(cuts?|raises?|hikes?|holds?|keeps?|reduces?)\b.{0,40}\b(rates?)\b'),
    ('Oil supply decision', r'\bopec\b.{0,70}\b(announces?|cuts?|raises?|increases?|reduces?)\b.{0,50}\b(output|production|supply)\b'),
)


def fresh(now):
    prototype = next(iter(s.fresh()['agents'].values()))
    agents = {k: copy.deepcopy(prototype) for k in NAMES}
    for a in agents.values():
        a.update(status='Collecting complete one-minute bars', last_exit_at=None,
                 last_signal_bar=None, day_halted=False)
    return dict(version=VERSION, policy=dict(POLICY), started_at=now.isoformat(), last_at=None,
                day=None, minute=None, minutes=[], candles=[], last_bar=None,
                agents=agents, seen={}, events=[], decisions=[], snapshot_at=None,
                coverage='Waiting for news', source='Upstox', complete_minutes=0)


def topic(heading):
    """Conservative event-topic labels, never a bullish/bearish sentiment claim."""
    if EXCLUDE.search(heading): return None
    return next((label for label, pattern in TOPICS if re.search(pattern, heading, re.I)), None)


def time_age(now, value):
    try: return (now-p.timestamp(value)).total_seconds()
    except (TypeError, ValueError, OverflowError): return None


def news_fresh(snapshot, now):
    age = time_age(now, snapshot.get('last_success_at'))
    return bool(snapshot.get('available') and age is not None and 0 <= age <= POLICY['feed_max_age'])


def ingest(state, snapshot, now):
    state['coverage'] = 'News available' if news_fresh(snapshot, now) else 'News unavailable or stale; news entries blocked'
    stamp = snapshot.get('last_success_at')
    if not stamp or stamp == state['snapshot_at']: return
    state['snapshot_at'] = stamp
    for article in snapshot.get('articles', []):
        ident = article.get('id')
        if not ident or ident in state['seen']: continue
        state['seen'][ident] = now.isoformat()
        heading = str(article.get('heading') or '')[:600]
        label = topic(heading)
        first = article.get('first_seen_at')
        publication = article.get('original_published_at') or article.get('published_at')
        published_age, received_age = time_age(now, publication), time_age(now, first)
        delay = None if published_age is None or received_age is None else published_age-received_age
        fingerprint = hashlib.sha256(re.sub(r'\W+', ' ', heading.lower()).strip().encode()).hexdigest()
        reason = None
        if not news_fresh(snapshot, now): reason = 'Feed unavailable or stale'
        elif not first or time_age(p.timestamp(first), state['started_at']) is None or p.timestamp(first) <= p.timestamp(state['started_at']): reason = 'Existing history before agent activation'
        elif not article.get('live_discovery'): reason = 'Startup/backfill or collection resumed after a gap'
        elif article.get('revised'): reason = 'Revised article; no fresh event assumed'
        elif delay is None or not 0 <= delay <= POLICY['publication_max_delay'] or not 0 <= published_age <= POLICY['event_lifetime'] or received_age < 0: reason = 'Late or inconsistent publication/receipt timestamps'
        elif not label: reason = 'No qualifying macro event; company news, commentary and recaps are context only'
        elif any(e['fingerprint'] == fingerprint or (e['topic'] == label and 0 <= time_age(now, e['received_at']) < 1800) for e in state['events']): reason = 'Duplicate headline or same macro topic within 30 minutes'
        else:
            state['events'].append(dict(id=ident, heading=heading, url=article.get('url'),
                published_at=publication, received_at=first, topic=label, fingerprint=fingerprint,
                used=False, rule_version=VERSION))
            reason = 'Event candidate; awaiting a completed price breakout after receipt'
        state['decisions'].append(dict(at=now.isoformat(), id=ident, heading=heading,
            url=article.get('url'), published_at=publication, received_at=first, reason=reason))
    # Bounded persistent dedup history. Old publications cannot re-arm later.
    state['seen'] = {k:v for k,v in state['seen'].items() if (time_age(now,v) or 0) <= 8*86400}
    state['events'] = state['events'][-200:]
    state['decisions'] = state['decisions'][-100:]


def active_event(state, now, bar_start):
    for event in reversed(state['events']):
        age = time_age(now, event['published_at'])
        if not event['used'] and age is not None and 0 <= age <= POLICY['event_lifetime'] and p.timestamp(event['received_at']).timestamp() <= bar_start:
            return event
    return None


def breakout(bars):
    if len(bars) < 4: return None
    bars = bars[-4:]
    if any(b['at']-a['at'] != 60 for a,b in zip(bars,bars[1:])): return None
    prior, last = bars[:-1], bars[-1]
    high, low = max(b['high'] for b in prior), min(b['low'] for b in prior)
    # Frozen exploratory parameters; not tuned to today's outcomes.
    if (high-low)/last['close'] > .004: return None
    if high*1.0003 < last['close'] <= high*1.006: return 'CE'
    if low*.994 <= last['close'] < low*.9997: return 'PE'
    return None


def usable(row, now, entry=True):
    try:
        age = time_age(now, row.get('quote_at'))
        dte = (datetime.fromisoformat(row['expiry']).date()-now.astimezone(p.IST).date()).days
        return (row.get('provider') == 'upstox' and row.get('underlying_key') == 'NSE_INDEX|Nifty 50'
                and row.get('option_type') in ('CE','PE') and p.valid_quote(row)
                and age is not None and 0 <= age <= 5
                and min(float(row['bid_size']),float(row['ask_size'])) >= row['lot_size']
                and (2 <= dte <= 14 if entry else dte >= 0))
    except (ValueError, TypeError, KeyError): return False


def fill(leg, quotes, now, entry, signal_at=None):
    q = quotes.get(leg['instrument_key'])
    if not q or not usable(q, now, entry): return None
    if any(q[k] != leg[k] for k in ('option_type','strike','expiry','lot_size')): return None
    if signal_at and p.timestamp(q['quote_at']) <= p.timestamp(signal_at): return None
    side = 'BUY' if entry else 'SELL'
    price = float(q['ask'])*1.005 if entry else float(q['bid'])*.995
    return dict(instrument_key=q['instrument_key'],option_type=q['option_type'],strike=q['strike'],
                expiry=q['expiry'],lot_size=q['lot_size'],side=side,price=price,
                quote_at=q['quote_at'],charges=s.costs(price*q['lot_size'],side))


def entry_budget(a, f):
    debit = f['price']*f['lot_size'] + f['charges']['total']
    return debit <= min(POLICY['max_premium'], a['cash'])


def update_metrics(a):
    a['peak'] = max(a['peak'], a['equity'])
    a['max_drawdown'] = max(a['max_drawdown'], a['peak']-a['equity'])


def advance(state, rows, snapshot, now, allow_entries, calendar):
    at = now.isoformat(); local = now.astimezone(p.IST)
    if state['last_at'] and int(now.timestamp()) <= int(p.timestamp(state['last_at']).timestamp()): return
    day = local.date().isoformat(); minute = local.hour*60+local.minute
    new_day = day != state['day']
    gap = bool(state['last_at'] and time_age(now,state['last_at']) > 5)
    active = local.weekday() < 5 and 555 <= minute < 930
    ingest(state, snapshot, now)
    quotes = {x['instrument_key']:x for x in rows if usable(x, now, False)}
    spots = [p.number(x.get('spot')) for x in rows if x.get('provider') == 'upstox'
             and x.get('underlying_key') == 'NSE_INDEX|Nifty 50'
             and time_age(now,x.get('spot_at')) is not None and 0 <= time_age(now,x['spot_at']) <= 5]
    spots = [x for x in spots if x and x > 0]
    valid = active and bool(spots) and (max(spots)-min(spots))/min(spots) < .002
    if new_day or gap or not valid:
        state.update(minute=None,minutes=[],candles=[],last_bar=None)
    prior_bar = state['minutes'][-1]['at'] if state['minutes'] else None
    if valid: s.candle_sample(state,now,spots[0])
    bar = state['minutes'][-1] if state['minutes'] and state['minutes'][-1]['at'] != prior_bar else None
    state['complete_minutes'] = len(state['minutes'])
    side = breakout(state['minutes']) if bar else None
    clear = r.event_state(calendar,now) in ('CLEAR','POST_EVENT')
    for name,a in state['agents'].items():
        if new_day:
            a.update(daily_start=a['equity'],daily_entries=0,day_halted=False,pending=None,last_signal_bar=None)
        pos = a['position']
        if pos:
            if gap or new_day or not valid or not quotes.get(pos['legs'][0]['instrument_key']):
                if not a['blocked']: p.event(a,at,'data_gap','Position unresolved; next usable quote will be an explicitly flagged recovery exit')
                a['blocked']=True; a['day_halted']=True; pos['data_gap']=True
            f = fill(pos['legs'][0],quotes,now,False) if active else None
            if f is None:
                a['blocked']=True; a['day_halted']=True; pos['data_gap']=True
                a['status']='Unresolved position; waiting for a usable exit quote'
                continue
            a['equity'] = a['cash'] + s.cashflow([f]); pnl = a['equity']-pos['equity_before']
            move = f['price']/pos['legs'][0]['price']-1
            reason = ('Data-gap recovery at first usable quote' if a['blocked'] else
                      'Session exit' if minute >= 915 else
                      'Daily loss trigger' if a['equity'] <= a['daily_start']-POLICY['daily_loss'] else
                      '20-minute time exit' if time_age(now,pos['entry_at']) >= POLICY['max_hold_seconds'] else
                      'Premium stop' if move <= -POLICY['stop_pct'] else
                      'Premium target' if move >= POLICY['target_pct'] else None)
            if reason:
                a['cash']=a['equity']
                a['trades'].append(dict(**pos,exit_at=at,exit_legs=[f],exit_cost=f['charges']['total'],pnl=round(pnl,2),reason=reason))
                a.update(position=None,blocked=False,capital_reserved=0.,last_exit_at=at)
                p.event(a,at,'exit',reason)
            update_metrics(a)
            continue
        pending = a['pending']; a['pending']=None
        admission = (allow_entries and valid and not gap and not new_day and clear and 565 <= minute < 870
                     and not a['day_halted'] and a['equity'] > a['daily_start']-POLICY['daily_loss']
                     and a['daily_entries'] < POLICY['max_entries'])
        if name == 'news_reaction' and not news_fresh(snapshot,now): admission=False
        if pending:
            f = fill(pending['legs'][0],quotes,now,True,pending['signal_at']) if admission and 0 < time_age(now,pending['signal_at']) <= 5 else None
            ev = pending.get('news')
            if f and pending.get('trigger') and ((pending['legs'][0]['option_type']=='CE' and spots[0]<=pending['trigger']) or (pending['legs'][0]['option_type']=='PE' and spots[0]>=pending['trigger'])): f=None
            if ev and (time_age(now,ev['published_at']) > POLICY['event_lifetime'] or any(x.get('id') == ev['id'] and x.get('revised') for x in snapshot.get('articles',[]))): f=None
            if f and entry_budget(a,f):
                premium=f['price']*f['lot_size']; before=a['cash']
                a['position']=dict(legs=[f],entry_at=at,signal_at=pending['signal_at'],quantity=f['lot_size'],
                    equity_before=before,entry_cost=f['charges']['total'],news=ev,bar=pending['bar'],
                    data_gap=False,rule_version=VERSION,stop_loss=premium*POLICY['stop_pct'],target_profit=premium*POLICY['target_pct'])
                a['cash']+=s.cashflow([f]); a['capital_reserved']=premium
                liquidation=fill(f,quotes,now,False)
                a['equity']=a['cash']+s.cashflow([liquidation]); a['daily_entries']+=1
                p.event(a,at,'entry','Paper buy: one lot at next fresh ask plus slippage')
                update_metrics(a)
            else: p.event(a,at,'skip','Pending entry cancelled: quote, news, calendar or risk limit changed')
            continue
        if not admission:
            a['status']=('Entries paused' if not allow_entries else 'Daily risk limit / gap recovery lock' if a['day_halted'] or a['daily_entries']>=POLICY['max_entries'] or a['equity']<=a['daily_start']-POLICY['daily_loss'] else 'Review today’s event calendar' if not clear else 'News feed stale; entry blocked' if name=='news_reaction' and not news_fresh(snapshot,now) else 'Waiting for entry hours and fresh market data')
            continue
        if a['last_exit_at'] and time_age(now,a['last_exit_at']) < POLICY['cooldown_seconds']:
            a['status']='Ten-minute cooldown after exit'; continue
        if not bar or not side:
            a['status']='Waiting for four complete one-minute bars and a breakout'; continue
        if a['last_signal_bar']==bar['at']: continue
        a['last_signal_bar']=bar['at']
        ev=active_event(state,now,bar['at']) if name=='news_reaction' else None
        if name=='news_reaction' and (not ev or any(x.get('id')==ev['id'] and x.get('revised') for x in snapshot.get('articles',[]))):
            p.event(a,at,'skip','Price breakout without a qualifying fresh news event'); continue
        candidates=[q for q in quotes.values() if usable(q,now) and q['option_type']==side and abs(q['strike']-spots[0])<=100]
        if not candidates:
            p.event(a,at,'skip','No liquid near-ATM option 2–14 days from expiry'); continue
        q=min(candidates,key=lambda q:(q['expiry'],abs(q['strike']-spots[0])))
        indicative=fill(q,quotes,now,True)
        if not entry_budget(a,indicative):
            p.event(a,at,'skip','Nearest whole lot exceeds ₹5,000 premium and entry-fee cap'); continue
        if ev: ev['used']=True
        a['pending']=dict(legs=[dict(instrument_key=q['instrument_key'],option_type=q['option_type'],strike=q['strike'],expiry=q['expiry'],lot_size=q['lot_size'])],signal_at=at,news=copy.deepcopy(ev),bar=copy.deepcopy(bar),trigger=max(b['high'] for b in state['minutes'][-4:-1])*1.0003 if side=='CE' else min(b['low'] for b in state['minutes'][-4:-1])*.9997)
        p.event(a,at,'signal',f'{side} breakout; awaiting a newer option quote'+(' after news receipt' if ev else ' (price-only control)'))
    state.update(last_at=at,day=day)


def snapshot_from_db(db):
    import json
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='paper_news_status'").fetchone(): return {}
    row=db.execute('SELECT payload FROM paper_news_status WHERE id=1').fetchone()
    try: return json.loads(row[0]) if row else {}
    except (ValueError, TypeError): return {}


def dashboard(state):
    if not state: return None
    agents=p.summary(dict(agents=state['agents']))['agents']
    for name,a in agents.items():
        a['data_gap_trades']=sum(bool(t.get('data_gap')) for t in state['agents'][name]['trades'])
    return dict(version=state['version'],policy=state['policy'],started_at=state['started_at'],
                last_at=state['last_at'],complete_minutes=state['complete_minutes'],coverage=state['coverage'],
                events=state['events'][-10:],decisions=state['decisions'][-30:],agents=agents,
                comparison='Prospective paper experiment; differences are not yet evidence of a news edge')


def isolated_tick(parent, rows, snapshot, now, allow_entries):
    """A malformed news record cannot interrupt the existing eleven agents."""
    prior=parent.get('news_agent') or fresh(now)
    candidate=copy.deepcopy(prior)
    try:
        advance(candidate,rows,snapshot,now,allow_entries,parent.get('research',{}).get('calendar',{}))
        parent['news_agent']=candidate
    except (ValueError,KeyError,TypeError,OverflowError):
        parent['news_agent']=prior
        prior['coverage']='News agent error; new entries stopped until next valid evaluation'
        prior.update(minute=None,minutes=[],candles=[],last_bar=None,complete_minutes=0)
        for a in prior['agents'].values():
            a['pending']=None
            a['day_halted']=True
            if a['position']:
                a['blocked']=True
                a['position']['data_gap']=True
            a['status']='News agent evaluation error; account entries locked for the day'
