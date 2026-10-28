import unittest
from datetime import datetime,timezone
from track import update
class TrackingTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,26,10,tzinfo=timezone.utc)
  self.briefs={'observations':[{'id':'one','symbol':'TEST.NS','benchmark':'^NSEI','country':'IN','currency':'INR'}]}
 def quotes(self,prices):
  return {s:dict(symbol=s,currency='INR',history=[dict(date=d,adjustedClose=v) for d,v in prices]) for s in ['TEST.NS','^NSEI']}
 def test_no_backdating_or_same_day_baseline(self):
  d=update(None,self.briefs,self.quotes([('2026-10-23',100),('2026-10-26',110)]),self.now)
  self.assertIsNone(d['observations']['one']['baselineDate'])
  d=update(d,self.briefs,self.quotes([('2026-10-27',110),('2026-10-28',120)]),datetime(2026,10,29,tzinfo=timezone.utc))
  i=d['observations']['one'];self.assertEqual(i['baselineDate'],'2026-10-27');self.assertEqual(i['firstPublishedAt'],self.now.isoformat());self.assertAlmostEqual(i['series'][-1]['stockReturn'],9.090909)
  self.assertEqual(i['series'][-1]['excessPp'],0)
 def test_failed_prices_preserve_history_and_version_is_immutable(self):
  d=update(None,self.briefs,{},self.now)
  d=update(d,self.briefs,self.quotes([('2026-10-27',100),('2026-10-28',120)]),datetime(2026,10,29,tzinfo=timezone.utc))
  old=d['observations']['one']['series']
  self.assertEqual(update(d,self.briefs,{},self.now)['observations']['one']['series'],old)
  self.assertEqual(update(d,self.briefs,{},self.now)['observations']['one']['status'],'Tracking adjusted closes')
  self.briefs['observations'][0]['symbol']='WRONG.NS'
  self.assertIn('requires new version',update(d,self.briefs,{},self.now)['observations']['one']['status'])
 def test_currency_mismatch_rejected(self):
  q=self.quotes([('2026-10-27',100)])
  q['TEST.NS']['currency']='USD'
  d=update(None,self.briefs,q,self.now)
  self.assertIsNone(d['observations']['one']['baselineDate'])
if __name__=='__main__':unittest.main()
