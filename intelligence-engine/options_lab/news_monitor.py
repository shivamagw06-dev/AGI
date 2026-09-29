"""Shared read-only news observer. Never changes strategy state or places orders.

Rule matches are research labels, not verified event/impact assertions. HTTP runs
on a separate task/thread. Publication AND first-seen times prevent backdating.
"""
from __future__ import annotations
import asyncio
import csv
import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import paper_agents as p
from .upstox_live import load_access_token

VERSION = 'headline-rules-v1'
UNIVERSE_URL = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'
RULES = (
    ('Monetary policy', r'\b(rbi|reserve bank|fed|federal reserve)\b.{0,100}\b(rate|policy|decision|cut|hike)\b'),
    ('Geopolitical shock', r'\b(war|missile|invasion|military strike|sanctions|ceasefire)\b'),
    ('Market disruption', r'\b(trading halt|market crash|circuit breaker|exchange outage|emergency meeting)\b'),
    ('Company stress', r'\b(defaults?|fraud|bankruptcy|insolvency|moratorium|liquidity crisis)\b'),
)


def schema(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS paper_news_status(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS paper_news_articles(id TEXT PRIMARY KEY,first_seen TEXT NOT NULL,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS paper_news_observations(id TEXT PRIMARY KEY,at TEXT NOT NULL,agent TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS paper_news_observations_at ON paper_news_observations(at);
    ''')


def instruments(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    result = {f"NSE_EQ|{r['ISIN Code'].strip()}":r['Symbol'].strip() for r in rows}
    if len(result)!=50 or any(not re.fullmatch(r'NSE_EQ\|IN[A-Z0-9]{10}',k) for k in result):
        raise ValueError('Invalid constituent list')
    return result


def read_json(url, token):
    # Use the same requests transport verified against Upstox from Render.
    # Redirects remain disabled so credentials never reach another host.
    import requests
    with requests.get(url,headers={'Authorization':f'Bearer {token}','Accept':'application/json'},
                      timeout=8,allow_redirects=False,stream=True) as response:
        response.raise_for_status()
        if response.status_code!=200: raise ValueError('Unexpected news status')
        chunks=[];size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size>2_000_000: raise ValueError('News response too large')
            chunks.append(chunk)
    return json.loads(b''.join(chunks))


def fetch_news(keys, token, get=read_json):
    """Every batch/page must succeed. A bounded scan must never claim completeness."""
    items = []
    keys = list(keys)
    for offset in range(0,len(keys),30):
        batch = keys[offset:offset+30]
        for page in range(1,11):
            query = urllib.parse.urlencode(dict(category='instrument_keys',instrument_keys=','.join(batch),page_number=page,page_size=100))
            body = get('https://api.upstox.com/v2/news?'+query,token)
            meta = body.get('metadata',{}).get('page',{})
            total_pages = meta.get('total_pages')
            if (body.get('status')!='success' or not isinstance(body.get('data'),dict)
                or not isinstance(total_pages,int) or not 0<=total_pages<=10
                or meta.get('page_number')!=page):
                raise ValueError('Incomplete news response')
            for key, articles in body['data'].items():
                if key not in batch or not isinstance(articles,list): raise ValueError('Invalid news mapping')
                items.extend((key,a) for a in articles)
            if page>=total_pages: break
    return items


def normalize(items, symbols, now):
    result = {}
    for key, item in items:
        heading = str(item.get('heading') or '').strip()[:600]
        url = urllib.parse.urlsplit(str(item.get('article_link') or ''))
        if not heading or url.scheme!='https' or url.hostname not in ('upstox.com','www.upstox.com'): continue
        try: published = datetime.fromtimestamp(float(item['published_time'])/1000,timezone.utc)
        except (KeyError,ValueError,TypeError,OverflowError,OSError): continue
        if not 0<=(now-published).total_seconds()<=7*86400: continue
        canonical = urllib.parse.urlunsplit(('https','upstox.com',url.path,'',''))
        ident = hashlib.sha256(canonical.encode()).hexdigest()[:24]
        if ident not in result:
            reasons = [label for label,pattern in RULES if re.search(pattern,heading,re.I)]
            result[ident] = dict(id=ident,heading=heading,url=canonical,published_at=published.isoformat(),
                reasons=reasons,rule_version=VERSION,symbols=[],pause_until=(published+timedelta(minutes=30)).isoformat() if reasons else None)
        if symbols[key] not in result[ident]['symbols']: result[ident]['symbols'].append(symbols[key])
    return list(result.values())


def assessment(snapshot, now):
    fresh = bool(snapshot.get('available') and snapshot.get('last_success_at') and
                 0<=(now-p.timestamp(snapshot['last_success_at'])).total_seconds()<=180)
    if not fresh: return dict(status='unavailable',would_pause=None,article_ids=[],until=None)
    active = [a for a in snapshot.get('articles',[]) if a.get('pause_until') and
              p.timestamp(a['first_seen_at'])<=now<p.timestamp(a['pause_until'])]
    return dict(status='potential_risk' if active else 'no_rule_match',would_pause=bool(active),
                article_ids=sorted(a['id'] for a in active),until=max((a['pause_until'] for a in active),default=None))


def poll(symbols, universe, *, now=None, get=read_json, live_collection=True):
    at = now or datetime.now(timezone.utc)
    with closing(p.database()) as db:
        schema(db)
        row=db.execute('SELECT payload FROM paper_news_status WHERE id=1').fetchone()
        previous=json.loads(row[0]) if row else {}
    snapshot=dict(previous,mode='observe',rule_version=VERSION,last_attempt_at=at.isoformat(),
                  universe=universe,instrument_count=len(symbols),refresh_seconds=60)
    try:
        articles=normalize(fetch_news(symbols,load_access_token(),get),symbols,at)
        completed=now or datetime.now(timezone.utc)
        with closing(p.database()) as db, db:
            schema(db)
            for article in articles:
                row=db.execute('SELECT first_seen,payload FROM paper_news_articles WHERE id=?',(article['id'],)).fetchone()
                old=json.loads(row[1]) if row else {}
                article['first_seen_at']=row[0] if row else completed.isoformat()
                article['original_published_at']=old.get('original_published_at',old.get('published_at',article['published_at']))
                article['original_heading']=old.get('original_heading',old.get('heading',article['heading']))
                article['revised']=bool(old.get('revised') or (row and (article['published_at']!=old.get('published_at') or article['heading']!=old.get('heading'))))
                article['live_discovery']=old.get('live_discovery',False) if row else bool(live_collection and previous.get('available') and previous.get('last_success_at') and 0<=(completed-p.timestamp(previous['last_success_at'])).total_seconds()<=180)
                db.execute('INSERT OR REPLACE INTO paper_news_articles VALUES(?,?,?)',
                           (article['id'],article['first_seen_at'],json.dumps(article)))
            # Do not repeatedly arm old stories after restarts or pagination changes.
            articles.sort(key=lambda a:a['published_at'],reverse=True)
            snapshot.update(available=True,error=None,last_success_at=completed.isoformat(),articles=articles)
            record_review(db,snapshot,completed)
            db.execute('INSERT OR REPLACE INTO paper_news_status VALUES(1,?)',(json.dumps(snapshot),))
            cutoff=(completed-timedelta(days=30)).isoformat()
            db.execute('DELETE FROM paper_news_articles WHERE first_seen<?',(cutoff,))
            db.execute('DELETE FROM paper_news_observations WHERE at<?',(cutoff,))
    except Exception as error:
        # Never log exception text/headers: may contain secrets or provider response.
        code=getattr(error,'code',None) or getattr(getattr(error,'response',None),'status_code',None)
        snapshot.update(available=False,error=f'News refresh failed ({"HTTP "+str(code) if code else type(error).__name__}); coverage unknown')
        with closing(p.database()) as db, db:
            schema(db)
            record_review(db,snapshot,at)
            db.execute('INSERT OR REPLACE INTO paper_news_status VALUES(1,?)',(json.dumps(snapshot),))
    return snapshot


def record_review(db,snapshot,now):
    decision=assessment(snapshot,now)
    signature=json.dumps([now.astimezone(p.IST).date().isoformat(),decision['status'],decision['article_ids']])
    if snapshot.get('review_signature')==signature:return
    snapshot['review_signature']=signature
    evidence=dict(decision,mode='observe',rule_version=VERSION,execution_changed=False,
                  headlines=[a for a in snapshot.get('articles',[]) if a['id'] in decision['article_ids']])
    db.execute('INSERT OR IGNORE INTO paper_news_observations VALUES(?,?,?,?,?)',
               ('review:'+now.isoformat(),now.isoformat(),'all','news_review',json.dumps(evidence)))


def agents(state):
    return dict(state.get('agents',{}),**state.get('spreads',{}).get('agents',{}),**state.get('research',{}).get('agents',{}))


def capture(state):
    return {key:{kind:(a.get(kind) or {}).get('entry_at' if kind=='position' else 'signal_at') for kind in ('pending','position')} for key,a in agents(state).items()}


def observe(db, state, before, now):
    """Read shared snapshot each tick; audit candidate/entry coincidences, never mutate state."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='paper_news_status'").fetchone(): return
    row=db.execute('SELECT payload FROM paper_news_status WHERE id=1').fetchone()
    if not row:return
    snapshot=json.loads(row[0]); decision=assessment(snapshot,now)
    for key,a in agents(state).items():
        for kind in ('pending','position'):
            value=a.get(kind)
            if not value:continue
            marker=value.get('entry_at' if kind=='position' else 'signal_at')
            if not marker or before.get(key,{}).get(kind)==marker:continue
            ident=hashlib.sha256(f'{key}|{kind}|{marker}'.encode()).hexdigest()
            evidence=dict(decision,mode='observe',rule_version=VERSION,news_checked_at=snapshot.get('last_success_at'),
                          actual_strategy_status=a.get('status'),entry_at=marker,execution_changed=False,
                          headlines=[a for a in snapshot.get('articles',[]) if a['id'] in decision['article_ids']])
            db.execute('INSERT OR IGNORE INTO paper_news_observations VALUES(?,?,?,?,?)',
                       (ident,now.isoformat(),key,'paper_entry' if kind=='position' else 'candidate',json.dumps(evidence)))


def dashboard(db, now):
    from . import yahoo_news
    yahoo=yahoo_news.dashboard(db,now)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='paper_news_status'").fetchone():
        return dict(mode='observe',status='unavailable',would_pause=None,articles=[],observations=[],yahoo=yahoo)
    row=db.execute('SELECT payload FROM paper_news_status WHERE id=1').fetchone()
    snapshot=json.loads(row[0]) if row else {}
    current=assessment(snapshot,now)
    recent=db.execute('SELECT at,agent,kind,payload FROM paper_news_observations ORDER BY at DESC LIMIT 30').fetchall()
    return dict(snapshot,**current,yahoo=yahoo,articles=snapshot.get('articles',[])[:20],
                observations=[dict(at=r[0],agent=r[1],kind=r[2],**json.loads(r[3])) for r in recent])


class NewsWorker:
    def __init__(self, stop):
        self.stop=stop
        self.symbols=instruments((Path(__file__).parent/'data/nifty50_news_watchlist.csv').read_text())
        self.universe='Bundled 50-stock watchlist; current membership unverified'
        self.universe_day=None

    def refresh_universe(self, day):
        try:
            with urllib.request.urlopen(UNIVERSE_URL,timeout=8) as r: text=r.read(100001).decode('utf-8-sig')
            self.symbols=instruments(text)
            self.universe='NSE NIFTY 50 constituent list verified '+day
        except Exception:
            self.universe='Last known 50-stock watchlist; current membership unverified'
        self.universe_day=day

    async def run(self):
        from .automation import _is_market_session
        from . import yahoo_news
        first=True
        yahoo_due=0
        while not self.stop.is_set():
            now=datetime.now(timezone.utc)
            if first or _is_market_session(now):
                try:
                    day=now.astimezone(p.IST).date().isoformat()
                    if self.universe_day!=day: await asyncio.to_thread(self.refresh_universe,day)
                    await asyncio.to_thread(poll,self.symbols,self.universe,live_collection=not first)
                    if now.timestamp() >= yahoo_due:
                        await asyncio.to_thread(yahoo_news.poll)
                        yahoo_due=now.timestamp()+yahoo_news.INTERVAL
                except Exception:
                    # Isolate disk/network failures from the one-second stream.
                    # Dashboard freshness expires even when this status write fails.
                    pass
                first=False
            try: await asyncio.wait_for(self.stop.wait(),timeout=60)
            except asyncio.TimeoutError: pass
