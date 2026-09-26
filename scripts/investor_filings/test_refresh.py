import unittest
from refresh import parse, normalized, latest_filings, refresh
from unittest.mock import patch

XML = b'''<xbrl xmlns:x="urn:x"><x:ISIN>INE000A01010</x:ISIN><x:Symbol>S0</x:Symbol><x:ScripCode>500000</x:ScripCode><x:NameOfTheCompany>Test company</x:NameOfTheCompany><context id="name"><period><endDate>2026-06-30</endDate></period><scenario><x:typedMember dimension="holder"><x:value>1</x:value></x:typedMember></scenario></context><context id="qty"><period><instant>2026-06-30</instant></period><scenario><x:typedMember dimension="holder"><x:value>1</x:value></x:typedMember></scenario></context><x:NameOfTheShareholder contextRef="name">Rekha Jhunjhunwala</x:NameOfTheShareholder><x:NumberOfShares contextRef="qty">1234</x:NumberOfShares><x:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="qty">0.0123</x:ShareholdingAsAPercentageOfTotalNumberOfShares></xbrl>'''
class FilingTests(unittest.TestCase):
    def test_dimensions_join_duration_to_instant(self):
        self.assertEqual(parse(XML,'2026-06-30'),[{'holder':'Rekha Jhunjhunwala','quantity':1234,'ownershipPct':1.23}])
    def test_other_period_rejected(self):
        with self.assertRaises(ValueError): parse(XML,'2026-03-31')
    def test_different_holder_context_not_joined(self):
        with self.assertRaises(ValueError): parse(XML.replace(b'<x:value>1</x:value>',b'<x:value>2</x:value>',1),'2026-06-30')
    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError): parse(XML.replace(b'>1234<',b'>-1<'),'2026-06-30')
    def test_group_not_inferred(self):
        self.assertNotEqual(normalized('SBI Group'),normalized('SBI Mutual Fund'))
        self.assertNotEqual(normalized('Rekha Jhunjhunwala'),normalized('Rakesh Jhunjhunwala and Associates'))
    def test_external_entities_rejected(self):
        with self.assertRaises(ValueError): parse(b'<!DOCTYPE x>'+XML,'2026-06-30')
    def test_revision_wins(self):
        row={'symbol':'ABC','name':'ABC Ltd','date':'30-JUN-2026','broadcastDate':'10-JUL-2026 10:00:00','xbrl':'https://nsearchives.nseindia.com/one.xml'}
        revised={**row,'broadcastDate':'11-JUL-2026 10:00:00','xbrl':'https://nsearchives.nseindia.com/two.xml'}
        self.assertEqual(latest_filings([revised,row])[0]['url'],revised['xbrl'])
    def test_foreign_source_not_downloaded(self):
        self.assertEqual(latest_filings([{'symbol':'ABC','date':'30-JUN-2026','xbrl':'https://example.com/a.xml'}]),[])
    def test_scan_retains_success_and_does_not_infer_sales(self):
        index = [{'symbol':f'S{i}','name':f'Company {i}','date':'30-JUN-2026','broadcastDate':'10-JUL-2026 10:00:00','xbrl':f'https://nsearchives.nseindia.com/{i}.xml'} for i in range(100)]
        with patch('refresh.targets', return_value=[{'name':'Rekha Jhunjhunwala','slug':'rekha'}]), patch('refresh.get', return_value=XML), patch('refresh.time.sleep'):
            first = refresh({}, index, 1)
            self.assertEqual(first['checkedCount'],1)
            self.assertEqual(len(first['profiles']['in-rekha']['rows']),1)
            with patch('refresh.get', side_effect=OSError('offline')):
                second = refresh(first,index,1)
            self.assertEqual(second['checkedCount'],1)
            self.assertEqual(second['profiles'],first['profiles'])
            self.assertEqual(second['pendingCount'],99)
    def test_incomplete_index_cannot_publish(self):
        with self.assertRaises(ValueError): refresh({},[],1)
if __name__=='__main__': unittest.main()
