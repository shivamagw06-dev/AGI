import unittest
from datetime import datetime,timezone
from refresh import value_profile, fingerprint, eligible
class ValuationTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,26,tzinfo=timezone.utc)
        self.p={'name':'Test','country':'IN','reportPeriod':'Jun 2026','rows':[{'stock':'Test Ltd','quantity':'1,000','history':['2%']}]}
        self.m={'IN':{'Test Ltd':{'symbol':'TEST.NS'}},'CUSIP':{}}
        self.q={'TEST.NS':dict(symbol='TEST.NS',currency='INR',type='EQUITY',price=110,previous=100,time=self.now.timestamp()-3600,splits=[])}
    def test_value_and_same_shares_change(self):
        v=value_profile(self.p,self.m,self.q,self.now)
        self.assertEqual(v['value'],110000);self.assertEqual(v['dayChangePct'],10)
        self.assertEqual(v['pricedCount'],1)
    def test_no_zero_for_missing_or_bad_price(self):
        for field,value in [('currency','USD'),('price',None),('time',self.now.timestamp()-9*86400),('symbol','WRONG'),('splits',[self.now.timestamp()-100])]:
            q={k:dict(v) for k,v in self.q.items()};q['TEST.NS'][field]=value
            self.assertIsNone(value_profile(self.p,self.m,q,self.now)['value'])
        self.assertIsNone(value_profile(self.p,self.m,{},self.now)['value'])
    def test_historical_options_unknown_excluded(self):
        for row in [dict(self.p['rows'][0],security='COM PUT SH'),dict(self.p['rows'][0],history=['-']),dict(self.p['rows'][0],quantity='-'),dict(self.p['rows'][0],stock='Unknown')]:
            self.assertIsNotNone(eligible(self.p,row,self.m)[1])
    def test_partial_and_fingerprint(self):
        before=fingerprint(self.p)
        self.p['rows'].append(dict(stock='Unknown',quantity='4',history=['2%']))
        v=value_profile(self.p,self.m,self.q,self.now)
        self.assertEqual(v['rowCount'],2);self.assertEqual(v['pricedCount'],1)
        self.assertNotEqual(before,fingerprint(self.p))
    def test_explicit_source_ticker_and_full_date(self):
        self.p.update(country='US',kind='fund-disclosures',reportPeriod='30 Jun 2026')
        self.p['rows'][0]['stock']='AAPL - Apple Inc.'
        self.q={'AAPL':dict(symbol='AAPL',currency='USD',type='EQUITY',price=110,previous=100,time=self.now.timestamp()-3600,splits=[])}
        self.assertEqual(value_profile(self.p,self.m,self.q,self.now)['value'],110000)
    def test_old_or_future_disclosure_excluded(self):
        for period in ['Jun 2023','Dec 2026','unknown']:
            self.p['reportPeriod']=period
            self.assertIsNone(value_profile(self.p,self.m,self.q,self.now)['value'])
if __name__=='__main__': unittest.main()
