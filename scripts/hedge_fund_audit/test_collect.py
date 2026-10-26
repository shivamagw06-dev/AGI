import json,unittest
from pathlib import Path
from collect import parse_table,aggregate,compare,apply_reviews

class SourceAuditTests(unittest.TestCase):
 def row(self,quantity=10,option='',unit='SH',securityClass='COM'):
  return dict(cusip='123456789',issuer='Example',securityClass=securityClass,unit=unit,option=option,quantity=quantity,value=100)
 def test_options_and_principal_are_never_folded_into_stock(self):
  rows=[self.row(),self.row(option='PUT'),self.row(unit='PRN')]
  self.assertEqual(len(aggregate(rows)),3)
  changes=compare([self.row(12),self.row(99,option='PUT'),self.row(500,unit='PRN')],rows)
  self.assertEqual(len(changes),1);self.assertEqual(changes[0]['quantityChangePct'],20)
 def test_discretion_rows_combine_but_class_wording_conflicts_are_flagged(self):
  changes=compare([self.row(10,securityClass='SPONSORED ADS'),self.row(10,securityClass='SPONSORED ADS')],[self.row(20,securityClass='SPON ADS')])
  self.assertEqual(changes,[])
  changes=compare([self.row(25,securityClass='SPONSORED ADS')],[self.row(20,securityClass='SPON ADS')])
  self.assertEqual(len(changes),1);self.assertTrue(changes[0]['identityReview'])
  self.assertNotEqual(changes[0]['status'],'New disclosure')
 def test_new_disclosures_have_no_invented_growth_rate(self):
  change=compare([self.row()],[])[0]
  self.assertIsNone(change['quantityChangePct']);self.assertEqual(change['status'],'New disclosure')
 def test_namespace_parser_rejects_invalid_quantities(self):
  raw=b'<informationTable xmlns="x"><infoTable><nameOfIssuer>X</nameOfIssuer><cusip>123456789</cusip><titleOfClass>COM</titleOfClass><value>100</value><shrsOrPrnAmt><sshPrnamt>10</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt><putCall>Put</putCall></infoTable></informationTable>'
  self.assertEqual(parse_table(raw)[0]['option'],'PUT')
  with self.assertRaises(ValueError):parse_table(raw.replace(b'>10<',b'>unknown<'))
 def test_split_resolution_requires_reviewed_date_and_ratio(self):
  record=dict(slug='example',status='SEC table checked',latest={'period':'2026-06-30'},secondary={'quantityMismatches':[dict(symbol='MNST',quantity=20,secQuantity=10),dict(symbol='APH',quantity=50,secQuantity=10)]})
  report={'managers':[record]};apply_reviews(report)
  self.assertEqual(len(record['secondary']['splitBasisComparisons']),1)
  self.assertEqual(record['secondary']['quantityMismatches'][0]['symbol'],'APH')
 def test_snapshot_has_complete_source_coverage_and_honest_secondary_counts(self):
  p=json.loads((Path(__file__).resolve().parents[2]/'public/data/hedge-fund-source-audit.json').read_text())
  self.assertEqual(p['managerCount'],len(p['managers']));self.assertEqual(len(set(m['cik'] for m in p['managers'])),p['managerCount'])
  for m in p['managers']:
   self.assertTrue(m['secUrl'].startswith('https://www.sec.gov/'))
   if m.get('latest'):
    self.assertTrue(m['latest']['tableSources'])
    self.assertEqual(m['sourceRowCount'],m['nonOptionShRows']+m['optionRows']+m['otherUnitRows'])
   self.assertTrue(all(not c.get('identityReview') for c in m.get('changes',[])))
   s=m['secondary'];self.assertLessEqual(len(s.get('quantityMismatches',[]))+len(s.get('splitBasisComparisons',[])),s.get('matchedQuantityRows',0))

if __name__=='__main__':unittest.main()
