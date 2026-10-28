import unittest
from snapshot import normalized_snapshot


class SnapshotTests(unittest.TestCase):
    def test_full_snapshot_aggregates_discretion_but_excludes_options_and_principal(self):
        rows = [dict(cusip='ONE', issuer='Company', securityClass='COM', quantity=q, unit=unit, option=option)
                for q, unit, option in [(10, 'SH', ''), (20, 'SH', ''), (100, 'SH', 'PUT'), (200, 'PRN', '')]]
        changes = [dict(cusip='ONE', quantityChange=15)]
        report = dict(checkedAt='2026-10-26', managers=[dict(auditHoldings=rows, changes=changes)])
        saved = normalized_snapshot(report)['managers'][0]
        self.assertEqual(len(saved['holdings']), 1)
        self.assertEqual(saved['holdings'][0]['quantity'], 30)
        self.assertEqual(saved['changes'], changes)
        self.assertEqual(len(report['managers'][0]['auditHoldings']), 4)


if __name__ == '__main__':
    unittest.main()
