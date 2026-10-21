"""Synthetic fixtures exercise identity safety; no fixture is published."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'intelligence-engine'))
import unittest
from financial_warehouse_completion.investor_mapping import build_profiles, seeds
from financial_warehouse_completion.shareholding_xml import import_bse
from test_refresh import XML
from bse import collect_bse
from unittest.mock import patch

PERSON={'id':'in-test','name':'Test Family','category':'individual'}
def filing(exchange='NSE',period='2026-06-30',quantity=100):
 return {'status':'ok','isin':'INE000A01010','scripCode':'500000','symbol':'TEST','stock':'Test Co','period':period,'url':'https://www.bseindia.com/test.xml','exchange':exchange,'rows':[{'holder':'Full Legal Name','quantity':quantity,'ownershipPct':1.0}]}
def rule(**changes):
 return {'id':'1','profileId':'in-test','holder':'Full Legal Name','scope':'TEST','bucket':'family','validFrom':'2026-06-30','validTo':None,'status':'approved','evidenceUrl':'https://example.com/evidence',**changes}
class MappingTests(unittest.TestCase):
 def test_approved_alias_only(self):
  p,_=build_profiles([PERSON],[filing()],[]);self.assertEqual(p['in-test']['rows'],[])
  p,_=build_profiles([PERSON],[filing()],[rule()]);self.assertEqual(len(p['in-test']['rows']),1)
 def test_scope_and_effective_period(self):
  for r in [rule(scope='OTHER'),rule(validFrom='2026-07-01'),rule(validTo='2026-06-01'),rule(status='revoked')]:
   p,_=build_profiles([PERSON],[filing()],[r]);self.assertEqual(p['in-test']['rows'],[])
 def test_dual_listing_dedup_and_latest_period(self):
  p,_=build_profiles([PERSON],[filing(),filing('BSE')],[rule()]);self.assertEqual(len(p['in-test']['rows']),1)
  p,_=build_profiles([PERSON],[filing(),filing('BSE','2026-09-30',150)],[rule()]);self.assertEqual(p['in-test']['rows'][0]['quantity'],150)
 def test_cross_exchange_conflict_is_withheld_without_revision_order(self):
  p,c=build_profiles([PERSON],[filing(),filing('BSE',quantity=200)],[rule()])
  self.assertEqual(p['in-test']['rows'],[]);self.assertEqual(c[0]['kind'],'filing-conflict')
 def test_duplicates_not_summed(self):
  f=filing();f['rows']*=2
  p,_=build_profiles([PERSON],[f],[rule()]);self.assertEqual(p['in-test']['rows'],[])
 def test_managed_bucket_remains_managed(self):
  p,_=build_profiles([PERSON],[filing()],[rule(bucket='managed')]);self.assertEqual(p['in-test']['rows'][0]['bucket'],'managed')
 def test_scoped_revocation_overrides_global(self):
  p,_=build_profiles([PERSON],[filing()],[rule(scope='*'),rule(status='revoked')]);self.assertEqual(p['in-test']['rows'],[])
 def test_expired_rejection_does_not_block_current_exact_match(self):
  person={**PERSON,'name':'Full Legal Name'}
  p,_=build_profiles([person],[filing()],[rule(status='rejected',validTo='2026-03-31')]);self.assertEqual(len(p['in-test']['rows']),1)
 def test_bse_import_validates_issuer_and_excludes_identifiers(self):
  payload={'xml':XML.decode(),'scripCode':'500000','period':'2026-06-30','sourceUrl':'https://www.bseindia.com/test.xml'}
  self.assertEqual(import_bse(payload)['rows'][0]['quantity'],1234)
  with self.assertRaises(ValueError):import_bse({**payload,'scripCode':'500001'})
  with self.assertRaises(ValueError):import_bse({**payload,'period':'2026-03-31'})
 def test_missing_bse_connection_retains_imports_and_reports_gap(self):
  with patch.dict('os.environ',{'BSE_SHAREHOLDING_FEED_URL':''}):
   rows,status=collect_bse([filing('BSE')],[],None,None,None)
  self.assertEqual(len(rows),1);self.assertEqual(status['state'],'not_configured')
 def test_all_seeds_validate(self):self.assertGreaterEqual(len(seeds()),9)
if __name__=='__main__':unittest.main()
