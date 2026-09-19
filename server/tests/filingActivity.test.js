import test from 'node:test';
import assert from 'node:assert/strict';
import {
  activityCounts, topWeight, turnover, holdingTenure, averageTenure, topKeys, valueFlow,
} from '../services/filingActivity.js';

const berkshireish = [
  { cusip: 'AAPL', value_usd: 66_000_000_000 },
  { cusip: 'AXP', value_usd: 50_000_000_000 },
  { cusip: 'BAC', value_usd: 30_000_000_000 },
  ...Array.from({ length: 26 }, (_, i) => ({ cusip: `S${i}`, value_usd: 1_000_000_000 })),
];

test('concentration is computed from value, not from a stored weight', () => {
  // A filing whose weights were written under a different value scale must not
  // be able to report a concentration its own numbers contradict.
  const pct = topWeight(berkshireish, 10);
  const total = berkshireish.reduce((s, r) => s + r.value_usd, 0);
  const top10 = [66, 50, 30, 1, 1, 1, 1, 1, 1, 1].reduce((s, v) => s + v * 1e9, 0);
  assert.ok(Math.abs(pct - (top10 / total) * 100) < 1e-9);
});

test('puts and calls are outside the book being described', () => {
  const withOptions = [...berkshireish, { cusip: 'P', value_usd: 9e12, put_call: 'PUT' }];
  assert.equal(topWeight(withOptions, 10), topWeight(berkshireish, 10));
});

test('the two turnover figures answer different questions', () => {
  // A manager can open and close many small positions - high turnover by
  // count - while barely moving money. Reporting one figure hides that.
  const changes = [
    { change_type: 'new', current_value: 1_000_000 },
    { change_type: 'exited', previous_value: 900_000 },
    { change_type: 'increased' },
    { change_type: 'reduced' },
  ];
  const holdings = [{ value_usd: 500_000_000 }, { value_usd: 500_000_000 }];
  const t = turnover(changes, holdings);
  assert.equal(t.byCount, 100);              // two of two positions changed hands
  assert.ok(t.byValue < 0.1);                 // but almost none of the money moved
});

test('a position held every quarter collected is reported as a floor', () => {
  // Twelve quarters of filings cannot show a position held for thirty-six.
  // Reporting the truncation as the answer describes the fetch depth, not the
  // manager.
  const periods = ['2026-06-30', '2026-03-31', '2025-12-31'];
  const byPeriod = new Map(periods.map((p) => [p, new Set(['AAPL', 'AXP'])]));
  const tenure = holdingTenure(periods, byPeriod, '2026-06-30');
  assert.equal(tenure.get('AAPL'), 3);

  const avg = averageTenure(tenure, ['AAPL', 'AXP'], 3);
  assert.equal(avg.quarters, 3);
  assert.equal(avg.truncated, true, 'the real holding period is longer than the history');
});

test('a position newly opened is not reported as truncated', () => {
  const periods = ['2026-06-30', '2026-03-31', '2025-12-31'];
  const byPeriod = new Map([
    ['2026-06-30', new Set(['NEW'])],
    ['2026-03-31', new Set()],
    ['2025-12-31', new Set()],
  ]);
  const avg = averageTenure(holdingTenure(periods, byPeriod, '2026-06-30'), ['NEW'], 3);
  assert.equal(avg.quarters, 1);
  assert.equal(avg.truncated, false);
});

test('a position sold and rebought is held since the rebuy', () => {
  // A gap ends the run. Counting it as continuous would credit the manager
  // with conviction it did not have.
  const periods = ['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'];
  const byPeriod = new Map([
    ['2026-06-30', new Set(['X'])],
    ['2026-03-31', new Set(['X'])],
    ['2025-12-31', new Set()],        // sold
    ['2025-09-30', new Set(['X'])],   // held before that
  ]);
  assert.equal(holdingTenure(periods, byPeriod, '2026-06-30').get('X'), 2);
});

test('the largest positions are picked by value', () => {
  assert.deepEqual(topKeys(berkshireish, 3, (r) => r.cusip), ['AAPL', 'AXP', 'BAC']);
});

test('quarter-over-quarter flow, and no division by a missing prior', () => {
  const flow = valueFlow(299_000_000_000, 263_000_000_000);
  assert.ok(Math.abs(flow.changePct - 13.688) < 0.01);
  assert.equal(valueFlow(299e9, 0).changePct, null, 'a first filing has no prior to compare');
});

test('an empty book yields nothing rather than zero', () => {
  // Zero concentration and zero turnover read as facts about the manager.
  assert.equal(topWeight([], 10), null);
  assert.equal(turnover([], []).byCount, null);
  assert.equal(averageTenure(new Map(), [], 12).quarters, null);
});
