import test from 'node:test';
import assert from 'node:assert/strict';
import { afterMarketClose, dailyCoveragePassed } from './hedgeFundUpstoxCandleScheduler.js';

test('full-universe EOD refresh opens only after the NSE close buffer', () => {
  assert.equal(afterMarketClose(new Date('2026-08-14T10:14:00Z')), false); // 15:44 IST
  assert.equal(afterMarketClose(new Date('2026-08-14T10:15:00Z')), true);  // 15:45 IST
  assert.equal(afterMarketClose(new Date('2026-08-15T11:00:00Z')), false); // Saturday
});

test('partial EOD runs cannot seal the daily refresh', () => {
  assert.equal(dailyCoveragePassed({ latest_session_coverage: 159 }, 200), false);
  assert.equal(dailyCoveragePassed({ latest_session_coverage: 160 }, 200), true);
  assert.equal(dailyCoveragePassed({ latest_session_coverage: 200 }, 200), true);
  assert.equal(dailyCoveragePassed(null, 200), false);
});
