import unittest
from datetime import datetime,timezone,timedelta
from publish import validate,BRANCH,FILE
class PublicationTests(unittest.TestCase):
    def sample(self):
        return {'schemaVersion':1,'updatedAt':datetime.now(timezone.utc).isoformat(),'profiles':{'test':{'pricedCount':1}}}
    def test_current_data_accepted_and_source_branch_not_modified(self):
        validate(self.sample());self.assertEqual(BRANCH,'investor-valuation-data');self.assertEqual(FILE,'investor-valuations/latest.json')
    def test_old_or_future_data_rejected(self):
        for delta in [-2,2]:
            d=self.sample();d['updatedAt']=(datetime.now(timezone.utc)+timedelta(days=delta)).isoformat()
            with self.assertRaises(ValueError):validate(d)
    def test_empty_snapshot_rejected(self):
        d=self.sample();d['profiles']['test']['pricedCount']=0
        with self.assertRaises(ValueError):validate(d)
