"""Private prelaunch sponsorship applications. No payment or rank can be granted here."""
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import urlsplit

CATEGORIES = ['Research & Data', 'Financial Modeling', 'Accounting', 'Portfolio Tools', 'AI for Finance', 'Professional Services']

@contextmanager
def connection():
    from institutional_warehouse.db import store_root
    db = sqlite3.connect(store_root() / 'finance_tools.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.execute('CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, owner TEXT NOT NULL, url TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL, reviewed_by TEXT, reviewed_at TEXT, UNIQUE(owner,url))')
        yield db
        db.commit()
    finally:
        db.close()

def submit(payload):
    owner = str(payload.get('owner', ''))
    email = str(payload.get('email', ''))
    if not owner or not email: raise ValueError('Verified account required')
    data = {}
    for key, minimum, maximum in [('name', 2, 70), ('description', 20, 280), ('url', 8, 300)]:
        value = str(payload.get(key, '')).strip()
        if not minimum <= len(value) <= maximum: raise ValueError(f'Invalid {key}')
        data[key] = value
    try:
        url = urlsplit(data['url'])
        host = url.hostname or ''
        if url.scheme != 'https' or url.username or url.password or url.port not in (None, 443) or not re.fullmatch(r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}', host): raise ValueError()
        if host.endswith(('.local', '.localhost', '.internal')): raise ValueError()
    except ValueError: raise ValueError('Use a public HTTPS website address')
    data['url'] = 'https://' + host.lower() + (url.path.rstrip('/') or '')
    if payload.get('category') not in CATEGORIES: raise ValueError('Choose a category')
    if payload.get('authorized') is not True: raise ValueError('Confirm that you represent this business')
    budget = payload.get('budget')
    if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= 1000000: raise ValueError('Budget must be whole rupees from 1 to 1,000,000')
    data.update(category=payload['category'], budget=budget, email=email)
    now = datetime.now(timezone.utc).isoformat()
    with connection() as db:
        previous = db.execute('SELECT id FROM applications WHERE owner=? AND url=?', (owner, data['url'])).fetchone()
        if previous: return {'ok': True, 'id': previous['id'], 'duplicate': True}
        if db.execute('SELECT count(*) FROM applications WHERE owner=?', (owner,)).fetchone()[0] >= 10: raise ValueError('Maximum 10 applications per account')
        identity = str(uuid.uuid4())
        db.execute('INSERT INTO applications(id,owner,url,created,status,data) VALUES(?,?,?,?,?,?)', (identity, owner, data['url'], now, 'pending', json.dumps(data)))
    return {'ok': True, 'id': identity}

def applications(owner=None):
    with connection() as db:
        rows = db.execute('SELECT * FROM applications WHERE owner=? ORDER BY created DESC', (owner,)).fetchall() if owner else db.execute('SELECT * FROM applications ORDER BY created DESC LIMIT 1000').fetchall()
    return {'ok': True, 'applications': [dict(id=r['id'], created=r['created'], status=r['status'], **json.loads(r['data'])) for r in rows]}

def review(identity, payload):
    status = payload.get('status')
    if status not in {'reviewed', 'rejected', 'pending'}: raise ValueError('Invalid review status')
    actor = str(payload.get('actor', ''))
    if not actor: raise ValueError('Reviewer required')
    with connection() as db:
        changed = db.execute('UPDATE applications SET status=?,reviewed_by=?,reviewed_at=? WHERE id=?', (status, actor, datetime.now(timezone.utc).isoformat(), identity)).rowcount
        if not changed: raise ValueError('Application not found')
    return {'ok': True}
