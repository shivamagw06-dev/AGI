import json
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from options_lab import data_evidence as e, year_history as y, groww_observer as g

class DataEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(e,'root',return_value=Path(self.tmp.name));self.patch.start()
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def test_calendar_chunks_no_overlap(self):
        chunks=list(y.windows('2025-10-01','2026-09-30'))
        self.assertEqual(chunks[0][0],'2025-10-01');self.assertEqual(chunks[-1][1],'2026-09-30')
        from datetime import date,timedelta
        for a,b in zip(chunks,chunks[1:]):self.assertEqual(date.fromisoformat(a[1])+timedelta(days=1),date.fromisoformat(b[0]))
    def test_groww_local_time_and_bad_candles(self):
        rows=y.normalize([['2026-09-30T09:15:00',100,102,99,101,20,0]])
        self.assertTrue(rows[0][0].endswith('+05:30'))
        self.assertEqual(y.normalize([['2026-09-30T09:15:00',100,102,99,101]])[0][5:],[None,None])
        with self.assertRaises(ValueError):y.normalize([['2026-09-30T09:15:00',100,90,99,101,20,0]])
    def test_cached_chunk_and_empty_gap(self):
        with patch.object(e,'storage',return_value={'free_bytes':10*1024**3}),patch.object(y.time,'sleep'),patch.object(y,'groww',return_value={'candles':[]}) as provider:
            y.collect_chunk('groww','NSE-NIFTY','2026-09-01','2026-09-02','spot','test')
            with closing(y.db()) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM gaps').fetchone()[0],1)
            provider.return_value={'candles':[['2026-09-01T09:15:00',100,102,99,101,20,0]]}
            y.collect_chunk('groww','NSE-NIFTY','2026-09-01','2026-09-02','spot','test')
            y.collect_chunk('groww','NSE-NIFTY','2026-09-01','2026-09-02','spot','test')
            self.assertEqual(provider.call_count,2)
            with closing(y.db()) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM gaps').fetchone()[0],0)
    def test_mapping_excludes_wrong_underlying_and_expired(self):
        base=dict(exchange='NSE',segment='FNO',underlying_symbol='NIFTY',instrument_type='PE',expiry_date='2026-10-06',exchange_token='123',strike_price='22500')
        result=g.select([base,{**base,'underlying_symbol':'BANKNIFTY'},{**base,'expiry_date':'2026-09-01'}],'2026-10-01',22450)
        self.assertEqual(result,[base])
    def test_timestamp_units_and_invalid(self):
        self.assertEqual(g.timestamp(1746156600),1746156600000)
        self.assertEqual(g.timestamp(1746156600000),1746156600000)
        self.assertIsNone(g.timestamp(float('nan')))
    def test_no_activation_on_read_and_no_ephemeral_downloads(self):
        self.assertEqual(e.start(),{'enabled':False})
        with patch.object(e,'storage',return_value={'persistent_mount_verified':False}),patch.object(e.subprocess,'Popen') as child:
            result=e.start(True)
            self.assertIn('blocked',result);child.assert_not_called()
            self.assertNotIn('token',json.dumps(e.read('config')))

if __name__=='__main__':unittest.main()
