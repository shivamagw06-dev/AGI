from contextlib import closing
import sqlite3
import tempfile
import unittest
import urllib.error
from pathlib import Path
from shared_market_budget import SharedMarketBudget

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'budget.sqlite'
        self.now=2000.
        self.b=SharedMarketBudget(self.path,clock=lambda:self.now,sleep=self.advance)
    def tearDown(self): self.tmp.cleanup()
    def advance(self,seconds): self.now+=seconds
    def seed(self,count,background=1):
        with closing(self.b.database()) as db, db:
            db.executemany('INSERT INTO requests VALUES(?,?)',[(self.now-100,background)]*count)
    def test_workers_share_reservations_and_leave_live_capacity(self):
        self.seed(550)
        other=SharedMarketBudget(self.path,clock=lambda:self.now,sleep=self.advance)
        with self.assertRaises(urllib.error.HTTPError): other.reserve('https://api.upstox.com/v3/historical-candle/x')
        other.reserve('https://api.upstox.com/v2/market-quote/quotes')
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],551)
    def test_full_window_deferred_and_expires(self):
        self.seed(800)
        with self.assertRaises(urllib.error.HTTPError):self.b.reserve('https://api.upstox.com/v2/market-quote/quotes')
        self.advance(1800)
        self.b.reserve('https://api.upstox.com/v2/market-quote/quotes')
    def test_cooldown_shared_between_workers(self):
        self.b.observe(429,{'Retry-After':'120'})
        other=SharedMarketBudget(self.path,clock=lambda:self.now,sleep=self.advance)
        with self.assertRaises(urllib.error.HTTPError):other.reserve('https://api.upstox.com/v2/market-quote/quotes')
        self.advance(121);other.reserve('https://api.upstox.com/v2/market-quote/quotes')
    def test_unrelated_public_source_does_not_consume_budget(self):
        self.b.reserve('https://assets.upstox.com/instruments.json')
        self.assertFalse(self.path.exists())

if __name__=='__main__':unittest.main()
