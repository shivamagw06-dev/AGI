"""First-party anonymous website events. No IPs, emails or query strings."""
import sqlite3
from contextlib import contextmanager
import re
import json
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from urllib.parse import urlsplit

IST = timezone(timedelta(hours=5, minutes=30))
EVENTS = {'page_view', 'signup_completed', 'model_download'}

def clean(payload):
    if payload.get('event') not in EVENTS: raise ValueError('Unsupported event')
    out = {'event': payload['event']}
    for field in ['id', 'visitor', 'session']:
        value = str(payload.get(field, ''))
        if not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', value): raise ValueError('Invalid event identity')
        out[field] = value
    path = str(payload.get('path', '')).split('?')[0].split('#')[0]
    if not re.fullmatch(r'/[a-zA-Z0-9_./-]{0,240}', path) or path.startswith('//'): raise ValueError('Invalid page')
    if path.startswith(('/admin', '/api', '/account', '/auth')): raise ValueError('Excluded page')
    # Private portfolio identifiers are not collected.
    out['path'] = '/portfolio' if path.startswith('/portfolio') else path
    ref = str(payload.get('referrer', ''))
    try: host = urlsplit('https://' + ref).hostname or ''
    except ValueError: host = ''
    out['referrer'] = host if re.fullmatch(r'[a-z0-9.-]{1,150}', host) else 'Direct / unknown'
    out['device'] = payload.get('device') if payload.get('device') in {'Desktop', 'Mobile', 'Tablet'} else 'Unknown'
    return out

@contextmanager
def connection():
    from institutional_warehouse.db import store_root
    # Private telemetry database, deliberately absent from workbook/export APIs.
    db = sqlite3.connect(store_root() / 'website_analytics.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.execute('CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, received_at TEXT NOT NULL, event_json TEXT NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS events_received ON events(received_at)')
        yield db
        db.commit()
    finally: db.close()

def collect(payload):
    event = clean(payload)
    now = datetime.now(timezone.utc).isoformat()
    with connection() as db:
        db.execute('INSERT INTO events(event_id,received_at,event_json) VALUES(?,?,?) ON CONFLICT(event_id) DO NOTHING', [event['id'],now,json.dumps(event)])
    return {'ok':True}

def summarize(records, days, now=None):
    now = now or datetime.now(timezone.utc)
    start = now.astimezone(IST).replace(hour=0,minute=0,second=0,microsecond=0) - timedelta(days=days-1)
    events = [(datetime.fromisoformat(r['received_at']),json.loads(r['event_json'])) for r in records]
    events = [(t,e) for t,e in events if start <= t <= now]
    pageviews = [(t,e) for t,e in events if e['event']=='page_view']
    visitors = {e['visitor'] for _,e in pageviews}
    sessions = {(e['visitor'],e['session']) for _,e in pageviews}
    per_visitor = defaultdict(set)
    for _,e in pageviews: per_visitor[e['visitor']].add(e['session'])
    counts = Counter(t.astimezone(IST).date().isoformat() for t,_ in pageviews)
    def ranked(field):
        return [{'label':k,'views':v} for k,v in Counter(e[field] for _,e in pageviews).most_common(30)]
    return {'ok':True,'days':days,'timezone':'Asia/Kolkata','updatedAt':now.isoformat(),
      'visitors':len(visitors),'visits':len(sessions),'pageviews':len(pageviews),
      'repeatVisitors':sum(len(v)>1 for v in per_visitor.values()),
      'active':len({e['visitor'] for t,e in pageviews if t>=now-timedelta(minutes=5)}),
      'signups':len({e['visitor'] for _,e in events if e['event']=='signup_completed'}),
      'downloads':sum(e['event']=='model_download' for _,e in events),
      'daily':[{'date':(start+timedelta(days=i)).date().isoformat(),'views':counts[(start+timedelta(days=i)).date().isoformat()]} for i in range(days)],
      'pages':ranked('path'),'referrers':ranked('referrer'),'devices':ranked('device')}

def report(days=7):
    if days not in {1,7,30,90}: raise ValueError('Invalid reporting range')
    now=datetime.now(timezone.utc)
    start=(now.astimezone(IST).replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=days-1)).astimezone(timezone.utc).isoformat()
    with connection() as db:
        rows=db.execute('SELECT received_at,event_json FROM events WHERE received_at >= ? ORDER BY received_at DESC LIMIT 50001',[start]).fetchall()
        first=db.execute('SELECT MIN(received_at) AS first_at FROM events').fetchone()
    if len(rows)>50000: raise ValueError('Too many events for this range; choose a shorter range.')
    result=summarize(rows,days,now)
    result['trackingSince']=first['first_at'] if first else None
    return result
