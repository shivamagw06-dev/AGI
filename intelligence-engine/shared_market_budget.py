"""Read-only broker HTTP allowance shared by Python workers on one disk.

The Node API has its own 800/30-minute allocation. Python shares another 800
across its workers, leaving 400 of the documented standard 2000-call window
unused. External clients/other hosts remain outside this accounting.
"""
from __future__ import annotations
import io
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from pathlib import Path
from email.utils import parsedate_to_datetime


class SharedMarketBudget:
    def __init__(self, path=None, clock=time.time, sleep=time.sleep):
        self.path = path
        self.clock, self.sleep = clock, sleep

    def database(self):
        path = Path(self.path or os.getenv('MARKET_DATA_BUDGET_DB') or
                    str(Path(os.getenv('KIP_DATA_DIR', './data')) / 'market_data_budget.sqlite3'))
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=3)
        db.execute('CREATE TABLE IF NOT EXISTS requests(at REAL NOT NULL, background INTEGER NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS requests_time ON requests(at)')
        db.execute('CREATE TABLE IF NOT EXISTS cooldown(id INTEGER PRIMARY KEY CHECK(id=1), until REAL NOT NULL)')
        return db

    def reserve(self, url):
        if urllib.parse.urlsplit(url).hostname != 'api.upstox.com':
            return
        path = urllib.parse.urlsplit(url).path
        background = not any(part in path for part in ('market-quote', '/option/chain', '/feed/', '/get-market-data-feed'))
        began = self.clock()
        while True:
            now = self.clock()
            with closing(self.database()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('DELETE FROM requests WHERE at<=?', (now-1800,))
                row = db.execute('SELECT until FROM cooldown WHERE id=1').fetchone()
                delay = max(0., (row[0] if row else 0)-now)
                windows = [(1, 4, False), (60, 120, False), (1800, 800, False)]
                if background:
                    windows += [(1, 2, True), (60, 80, True), (1800, 550, True)]
                for window, limit, only_background in windows:
                    clause = ' AND background=1' if only_background else ''
                    rows = db.execute('SELECT at FROM requests WHERE at>?'+clause+' ORDER BY at DESC LIMIT ?', (now-window, limit)).fetchall()
                    if len(rows) >= limit:
                        delay = max(delay, rows[-1][0]+window-now)
                if delay <= 0:
                    db.execute('INSERT INTO requests VALUES(?,?)', (now, int(background)))
                    return
            if self.clock()-began+delay > 15:
                raise urllib.error.HTTPError(url, 429, 'AGI market-data budget cooling down', {}, io.BytesIO(b'Budget deferred; retry next scheduled cycle'))
            self.sleep(min(delay, 1))

    def observe(self, status, headers=None):
        if status not in (401, 403, 429):
            return
        raw = (headers or {}).get('Retry-After', '')
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            try:
                seconds = parsedate_to_datetime(raw).timestamp()-self.clock()
            except (TypeError, ValueError, OverflowError):
                seconds = 60
        until = self.clock()+max(60, seconds)
        with closing(self.database()) as db, db:
            db.execute('INSERT INTO cooldown VALUES(1,?) ON CONFLICT(id) DO UPDATE SET until=MAX(until,excluded.until)', (until,))


budget = SharedMarketBudget()


def budgeted_urlopen(request, *args, **kwargs):
    url = request.full_url if isinstance(request, urllib.request.Request) else str(request)
    if urllib.parse.urlsplit(url).hostname != 'api.upstox.com':
        return urllib.request.urlopen(request, *args, **kwargs)
    if isinstance(request, urllib.request.Request) and request.get_method() != 'GET':
        raise ValueError('Market-data transport is read-only')
    budget.reserve(url)
    try:
        return urllib.request.urlopen(request, *args, **kwargs)
    except urllib.error.HTTPError as error:
        budget.observe(error.code, error.headers)
        raise


def budgeted_requests_get(url, **kwargs):
    import requests
    if urllib.parse.urlsplit(url).hostname != 'api.upstox.com':
        return requests.get(url, **kwargs)
    budget.reserve(url)
    response = requests.get(url, **kwargs)
    budget.observe(response.status_code, response.headers)
    return response
