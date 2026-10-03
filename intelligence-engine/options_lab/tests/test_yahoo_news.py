import unittest
from datetime import datetime, timezone
from options_lab import yahoo_news as y

class YahooNewsTests(unittest.TestCase):
    now=datetime(2026,9,29,6,tzinfo=timezone.utc)
    def feed(self, url='https://finance.yahoo.com/news/example', date='Tue, 29 Sep 2026 05:00:00 GMT'):
        return f'<rss><channel><item><title>India news</title><link>{url}</link><pubDate>{date}</pubDate></item></channel></rss>'.encode()
    def test_valid_and_deduped(self):
        raw=self.feed().replace(b'</channel>',self.feed().split(b'<channel>')[1].split(b'</channel>')[0]+b'</channel>')
        self.assertEqual(len(y.parse(raw,self.now)),1)
    def test_rejects_unsafe_links_and_dates(self):
        for url in ('javascript:alert(1)','https://evil.example/news','https://user@finance.yahoo.com/news'):
            self.assertEqual(y.parse(self.feed(url),self.now),[])
        self.assertEqual(y.parse(self.feed(date='Tue, 29 Sep 2026 07:00:00 GMT'),self.now),[])
    def test_rejects_entities_and_nonfeed(self):
        for raw in (b'<!DOCTYPE rss><rss><channel/></rss>',b'<html/>'):
            with self.assertRaises(ValueError): y.parse(raw,self.now)
    def test_iso_date(self):
        self.assertEqual(len(y.parse(self.feed(date='2026-09-29T05:00:00Z'),self.now)),1)
