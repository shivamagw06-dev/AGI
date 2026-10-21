import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { selectDailyRotation } from '../services/upstoxValuationRatiosRefresh.js';

const rows = ['EEE', 'AAA', 'DDD', 'BBB', 'CCC'].map((symbol, index) => ({
  symbol,
  isin: `INE0000000${String(index).padStart(2, '0')}`,
}));

describe('Upstox valuation-ratio daily rotation', () => {
  it('uses a stable symbol order regardless of warehouse read order', () => {
    const selected = selectDailyRotation(rows, {
      limit: 2,
      now: '2026-08-06T12:00:00Z',
    });

    assert.equal(selected.universeSize, 5);
    assert.equal(selected.companies.length, 2);
    assert.deepEqual(selected.companies.map((row) => row.symbol), ['CCC', 'DDD']);
  });

  it('moves the batch forward on the next day', () => {
    const first = selectDailyRotation(rows, { limit: 2, now: '2026-08-06T12:00:00Z' });
    const next = selectDailyRotation(rows, { limit: 2, now: '2026-08-07T12:00:00Z' });

    assert.notDeepEqual(first.companies.map((row) => row.symbol), next.companies.map((row) => row.symbol));
    assert.deepEqual(next.companies.map((row) => row.symbol), ['EEE', 'AAA']);
  });
});
