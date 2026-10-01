import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from options_lab import data_evidence as e, year_history as y, validation_pipeline as v
class ValidationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.patch=patch.object(e,'root',return_value=Path(self.tmp.name));self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def test_bad_chunk_is_gap_not_success(self):
  with patch.object(y,'collect_chunk',side_effect=ValueError('Invalid OHLC')),patch.object(y.time,'sleep'):
   y.collect_safe('groww','NSE-NIFTY','2026-01-01','2026-01-02','spot',None)
  with closing(y.db()) as db:
   self.assertEqual(db.execute('SELECT reason FROM gaps').fetchone()[0],'Invalid OHLC');self.assertEqual(db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],0)
 def test_storage_limit_still_stops(self):
  with patch.object(y,'collect_chunk',side_effect=ValueError('Less than 2 GiB free; collection paused')):
   with self.assertRaises(ValueError):y.collect_safe('groww','NSE-NIFTY','2026-01-01','2026-01-02','spot',None)
 def test_comparison_matches_timestamps_and_keeps_missing(self):
  with closing(y.db()) as db,db:
   for provider,key,at,c in [('upstox','NSE_INDEX|Nifty 50','2026-01-01T09:15:00+05:30',100),('groww','NSE-NIFTY','2026-01-01T09:15:00+05:30',101),('groww','NSE-NIFTY','2026-01-01T09:16:00+05:30',102)]:
    db.execute('INSERT INTO candles VALUES(?,?,?,?)',(provider,key,at,json.dumps([at,c,c,c,c,0,0])))
  r=v.compare_spot();self.assertEqual(r['matched_minutes'],1);self.assertEqual(r['above_5bps'],1);self.assertEqual(r['sessions']['groww']['unmatched_minutes'],1)
 def test_age_does_not_accept_naive_or_missing(self):
  from datetime import datetime,timezone
  now=datetime.now(timezone.utc);self.assertIsNone(v.age(None,now));self.assertIsNone(v.age('2026-01-01T10:00:00',now))
 def test_groww_splits_large_window(self):
  with patch.object(e,'storage',return_value={'free_bytes':10*1024**3}),patch.object(y,'groww',return_value={'candles':[]}) as req:
   y.collect_chunk('groww','NSE-NIFTY','2026-01-01','2026-01-28','spot',None)
  self.assertEqual(req.call_count,4)
 def test_candidates_recheck_live_gate_without_rerunning_backtest(self):
  report=dict(status='complete',statistical_candidates=['trend'],results={'kept':True})
  e.write('strategy_validation',report);e.write('data_comparison',dict(matched_minutes=10,gaps=[],above_5bps=0))
  e.write('live_validation',dict(paper_enabled=True,feeds={'upstox':{'fresh':True},'groww':{'fresh':False}},agents={}))
  self.assertEqual(v.refresh_candidates()['paper_candidates'],[])
  e.write('live_validation',dict(paper_enabled=True,feeds={'upstox':{'fresh':True},'groww':{'fresh':True}},agents={}))
  self.assertEqual(v.refresh_candidates()['paper_candidates'],['trend'])
  self.assertEqual(e.read('strategy_validation')['results'],{'kept':True})
 def test_provider_discrepancies_block_candidates(self):
  e.write('strategy_validation',dict(status='complete',statistical_candidates=['trend']))
  e.write('data_comparison',dict(matched_minutes=10,gaps=[],above_5bps=1))
  e.write('live_validation',dict(paper_enabled=True,feeds={'upstox':{'fresh':True},'groww':{'fresh':True}}))
  self.assertEqual(v.refresh_candidates()['paper_candidates'],[])
  self.assertIn('Provider price discrepancies need review',e.read('paper_watchlist')['blockers'])
if __name__=='__main__':unittest.main()

class GrowwMalformedCandleTests(unittest.TestCase):
 def test_invalid_price_types_are_validation_errors(self):
  for value in (None,{},[],True,'bad',float('nan')):
   with self.subTest(value=value),self.assertRaises(ValueError):
    y.normalize([['2025-12-08T09:00:00',value,100,100,100,1425,None]])
 def test_invalid_container(self):
  for value in (None,{},'bad'):
   with self.subTest(value=value),self.assertRaises(ValueError):y.normalize(value)
 def test_null_prices_preserved_as_gap_and_next_chunk_continues(self):
  import gzip
  with tempfile.TemporaryDirectory() as tmp,patch.object(e,'root',return_value=Path(tmp)),patch.object(e,'storage',return_value={'free_bytes':10*1024**3}),patch.object(y.time,'sleep'):
   bad=[['2025-12-08T09:00:00',None,None,None,None,1425,None]]
   good=[['2025-12-09T09:15:00',100,101,99,100,10,None]]
   with patch.object(y,'groww',side_effect=[{'candles':bad},{'candles':good}]):
    y.collect_safe('groww','TEST','2025-12-08','2025-12-08','future',None)
    y.collect_safe('groww','TEST','2025-12-09','2025-12-09','future',None)
   with closing(y.db()) as db:
    self.assertEqual(db.execute('SELECT reason FROM gaps').fetchall(),[('Invalid OHLC',)])
    self.assertEqual(db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],1)
    self.assertEqual(db.execute('SELECT COUNT(*) FROM candles').fetchone()[0],1)
   rejected=list(Path(tmp).glob('rejected-*.json.gz'));self.assertEqual(len(rejected),1)
   with gzip.open(rejected[0],'rt') as f:self.assertEqual(json.load(f),bad)
