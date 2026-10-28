import json,unittest
from pathlib import Path
from refresh import eligible
ROOT=Path(__file__).resolve().parents[2]
class MappingTests(unittest.TestCase):
 def test_reviewed_aliases_and_unresolved_security_are_explicit(self):
  mappings=json.loads((ROOT/'src/data/investorProfiles/priceMappings.json').read_text())
  self.assertEqual(mappings['IN']['RateGain Travel']['symbol'],'RATEGAIN.NS')
  self.assertEqual(mappings['IN']['PNB Housing Finance']['isin'],'INE572E01012')
  p={'country':'IN','reportPeriod':'Sep 2026'}
  r={'stock':'Priority Jewels','quantity':'100','history':['1.7%'],'reportPeriod':'Sep 2026'}
  self.assertEqual(eligible(p,r,mappings)[1],'Exact security mapping unavailable')
  r.update(stock='RateGain Travel',reportPeriod='Jun 2026')
  self.assertIn('Historical',eligible(p,r,mappings)[1])
if __name__=='__main__':unittest.main()
