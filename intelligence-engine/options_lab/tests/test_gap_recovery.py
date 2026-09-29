import copy
import json
import tempfile
import unittest
import zlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from options_lab import paper_agents as p

NOW = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)
ENTRY = '2026-09-29T04:41:36+00:00'

class GapRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = patch.object(p, 'paths', return_value=(Path(self.tmp.name)/'source', Path(self.tmp.name)/'paper'))
        self.paths.start(); self.addCleanup(self.paths.stop)
        self.clock = patch.object(p, 'datetime', wraps=datetime)
        self.clock.start().now.return_value = NOW
        self.addCleanup(self.clock.stop)
        p.control('start')
        self.state = p.fresh_state()
        self.state['agents']['opening_range'].update(cash=90800, equity=99200, blocked=True,
            daily_entries=1, position=dict(instrument_key='NSE_FO|40700', option_type='PE',
            strike=22550, expiry='2026-10-06', entry_at=ENTRY, entry_price=140,
            quantity=65, entry_cost=100, equity_before=100000))
        self.quote=dict(instrument_key='NSE_FO|40700', option_type='PE', strike=22550,
            expiry='2026-10-06', provider='upstox', underlying_key='NSE_INDEX|Nifty 50',
            captured_at=NOW.isoformat(), quote_at=NOW.isoformat(), bid=98, ask=99,
            lot_size=65, bid_size=325, volume=1000, oi=1000)
        self.save()

    def save(self):
        with p.database() as db:
            db.execute('UPDATE sessions SET state=? WHERE id=1',(json.dumps(self.state),))
            db.execute('INSERT OR REPLACE INTO second_frames VALUES (?,?)',
                (NOW.isoformat(),zlib.compress(json.dumps([self.quote]).encode())))

    def stored(self):
        with p.database() as db:
            return json.loads(db.execute('SELECT state FROM sessions WHERE id=1').fetchone()[0])

    def test_recovery_preserves_loss_risk_and_other_accounts_and_cannot_repeat(self):
        before=copy.deepcopy(self.state)
        trade=p.recover_legacy_position('opening_range',ENTRY)
        state=self.stored(); a=state['agents']['opening_range']
        self.assertAlmostEqual(a['cash'],90800+98*.995*65-p.fee(98*.995*65,p.POLICY))
        self.assertFalse(a['blocked']); self.assertIsNone(a['position'])
        self.assertEqual(a['daily_entries'],1); self.assertEqual(a['daily_start'],100000)
        self.assertEqual(state['agents']['mean_reversion'],before['agents']['mean_reversion'])
        self.assertEqual(trade['evidence_status'],'data_gap_recovery')
        self.assertEqual(trade['exit_at'],NOW.isoformat())
        self.assertLess(trade['pnl'],-2000)
        with self.assertRaises(ValueError): p.recover_legacy_position('opening_range',ENTRY)
        self.assertEqual(self.stored(),state)

    def test_unusable_quotes_and_wrong_entry_leave_state_untouched(self):
        original=copy.deepcopy(self.quote)
        for changes in [dict(quote_at='2026-09-29T05:59:00+00:00'),dict(bid_size=64),
                        dict(bid=110),dict(provider='other'),dict(instrument_key='other'),
                        dict(expiry='2026-10-07'),dict(quote_at='2026-09-29T06:01:00+00:00')]:
            with self.subTest(changes=changes):
                self.quote={**original,**changes}; self.save()
                with self.assertRaises(ValueError): p.recover_legacy_position('opening_range',ENTRY)
                self.assertEqual(self.stored(),self.state)
        self.quote=original; self.save()
        with self.assertRaises(ValueError): p.recover_legacy_position('opening_range','wrong')
        self.assertEqual(self.stored(),self.state)

    def test_stale_frame_and_closed_market_cannot_recover(self):
        with p.database() as db: db.execute('DELETE FROM second_frames')
        with self.assertRaises(ValueError): p.recover_legacy_position('opening_range',ENTRY)
        self.assertEqual(self.stored(),self.state)
        self.save()
        p.datetime.now.return_value=datetime(2026,9,29,12,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): p.recover_legacy_position('opening_range',ENTRY)
        self.assertEqual(self.stored(),self.state)
