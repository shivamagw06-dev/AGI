import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from financial_warehouse_completion.finance_tools import submit, applications, review

class FinanceToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = patch('institutional_warehouse.db.store_root', return_value=Path(self.temp.name))
        self.root.start()
        self.payload = dict(owner='member', email='member@example.test', name='A test tool', url='https://example.com/?tracking=yes', description='A useful research tool for analysts.', category='Analytics', budget=500, authorized=True)
    def tearDown(self):
        self.root.stop()
        self.temp.cleanup()
    def test_private_persistent_idempotent_review(self):
        first = submit(self.payload)
        self.assertEqual(submit(self.payload)['id'], first['id'])
        self.assertEqual(applications('different')['applications'], [])
        row = applications('member')['applications'][0]
        self.assertEqual(row['status'], 'pending')
        self.assertEqual(row['url'], 'https://example.com')
        review(first['id'], dict(status='reviewed', actor='admin'))
        self.assertEqual(applications()['applications'][0]['status'], 'reviewed')
        with self.assertRaises(ValueError): review(first['id'], dict(status='paid', actor='admin'))
    def test_validation(self):
        for invalid in [{'url':'javascript:alert(1)'}, {'url':'https://127.0.0.1'}, {'url':'https://user:password@example.com'}, {'authorized':False}, {'budget':-1}, {'budget':1.5}, {'budget':True}, {'category':'Invalid'}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): submit({**self.payload, **invalid})
