"""Yahoo's public RSS feed, displayed with attribution; never a trading input."""
import json
import hashlib
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from . import paper_agents as p

URL = 'https://finance.yahoo.com/rss/topstories'
INTERVAL = 300


def fetch():
    import requests
    with requests.get(URL, headers={'User-Agent':'AGI-News-Research/1.0',
                      'Accept':'application/rss+xml, application/xml'},
                      timeout=10, allow_redirects=False, stream=True) as r:
        r.raise_for_status()
        if r.status_code != 200: raise ValueError('Unexpected RSS status')
        chunks=[]; size=0
        for chunk in r.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000: raise ValueError('RSS response too large')
            chunks.append(chunk)
    return b''.join(chunks)


def parse(raw, now):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unsafe XML')
    root=ET.fromstring(raw)
    channel=root.find('channel')
    if root.tag != 'rss' or channel is None: raise ValueError('Invalid RSS feed')
    articles=[]; seen=set()
    for item in channel.findall('item')[:100]:
        heading=item.findtext('title') or ''
        url=item.findtext('link') or ''
        parts=urlsplit(url)
        if not heading or parts.scheme!='https' or parts.hostname not in ('finance.yahoo.com','www.yahoo.com','news.yahoo.com') or parts.username or parts.password: continue
        try:
            date=item.findtext('pubDate') or ''
            try: published=parsedate_to_datetime(date)
            except ValueError: published=datetime.fromisoformat(date.replace('Z','+00:00'))
            if published.tzinfo is None: continue
            published=published.astimezone(timezone.utc)
        except (ValueError,TypeError,OverflowError): continue
        if not 0 <= (now-published).total_seconds() <= 7*86400: continue
        ident=hashlib.sha256(url.encode()).hexdigest()[:24]
        if ident in seen: continue
        seen.add(ident)
        articles.append(dict(id=ident,heading=heading,url=url,published_at=published.isoformat(),source='Yahoo Finance'))
    articles.sort(key=lambda a:a['published_at'],reverse=True)
    return articles


def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS paper_yahoo_news(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')


def poll(*, now=None, get=fetch):
    at=now or datetime.now(timezone.utc)
    with closing(p.database()) as db:
        schema(db)
        row=db.execute('SELECT payload FROM paper_yahoo_news WHERE id=1').fetchone()
        previous=json.loads(row[0]) if row else {}
    snapshot=dict(previous,last_attempt_at=at.isoformat(),refresh_seconds=INTERVAL,source='Yahoo Finance',
                  feed_url=URL,scope='Global top stories; not complete India coverage',mode='display_only')
    try:
        articles=parse(get(),at)
        completed=now or datetime.now(timezone.utc)
        old={a['id']:a for a in previous.get('articles',[])}
        for article in articles:
            saved=old.get(article['id'],{})
            article['first_seen_at']=saved.get('first_seen_at',completed.isoformat())
            article['original_published_at']=saved.get('original_published_at',article['published_at'])
            article['updated_at']=completed.isoformat() if saved and any(saved.get(k)!=article[k] for k in ('heading','published_at')) else saved.get('updated_at')
        snapshot.update(available=True,error=None,last_success_at=completed.isoformat(),articles=articles)
    except Exception as error:
        code=getattr(getattr(error,'response',None),'status_code',None)
        snapshot.update(available=False,error='Yahoo refresh failed ('+('HTTP '+str(code) if code else type(error).__name__)+'); retained headlines may be stale')
    with closing(p.database()) as db, db:
        schema(db)
        db.execute('INSERT OR REPLACE INTO paper_yahoo_news VALUES(1,?)',(json.dumps(snapshot),))
    return snapshot


def dashboard(db, now):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='paper_yahoo_news'").fetchone(): return {}
    row=db.execute('SELECT payload FROM paper_yahoo_news WHERE id=1').fetchone()
    snapshot=json.loads(row[0]) if row else {}
    snapshot['fresh']=bool(snapshot.get('available') and snapshot.get('last_success_at') and
                           0 <= (now-p.timestamp(snapshot['last_success_at'])).total_seconds() <= 600)
    snapshot['latest_published_at']=max((a['published_at'] for a in snapshot.get('articles',[])),default=None)
    snapshot['content_recent']=bool(snapshot['latest_published_at'] and 0 <= (now-p.timestamp(snapshot['latest_published_at'])).total_seconds() <= 86400)
    return snapshot
