import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateSignalOutcome, createOutcomeSchedule, horizonDueAt, processDueOutcomes } from './alphaOutcomeTracker.js';

test('creates all seven forward measurement checkpoints', () => {
  const rows = createOutcomeSchedule({
    id: 'signal-1', as_of: '2026-08-10T05:50:00Z',
    price_at_signal: 100, nifty_at_signal: 25000, sector_at_signal: 50000,
  });
  assert.deepEqual(rows.map((row) => row.horizon), ['5m', '15m', '30m', '1h', 'close', 'next_day', '5d']);
  assert.equal(rows.find((row) => row.horizon === '5m').due_at, '2026-08-10T05:55:00.000Z');
  assert.equal(rows.find((row) => row.horizon === 'close').due_at, '2026-08-10T10:00:00.000Z');
});

test('moves next-day observations past a weekend', () => {
  assert.equal(horizonDueAt('2026-08-14T06:00:00Z', 'next_day'), '2026-08-17T10:00:00.000Z');
});

test('calculates market, sector and cost-adjusted outcomes', () => {
  const result = calculateSignalOutcome({
    direction: 'positive', priceAtSignal: 100, futurePrice: 102,
    niftyAtSignal: 100, futureNifty: 101, sectorAtSignal: 100, futureSector: 101.2,
    beta: 1.1, estimatedCostBps: 5,
  });
  assert.equal(result.stock_return_pct, 2);
  assert.equal(result.market_adjusted_alpha_pct, 0.9);
  assert.equal(result.sector_adjusted_alpha_pct, 0.8);
  assert.equal(result.net_alpha_pct, 0.75);
  assert.equal(result.positive_outcome, true);
});

test('reverses return interpretation for negative signals', () => {
  const result = calculateSignalOutcome({
    direction: 'negative', priceAtSignal: 100, futurePrice: 98,
    niftyAtSignal: 100, futureNifty: 100, sectorAtSignal: 100, futureSector: 99.5,
  });
  assert.equal(result.directional_return_pct, 2);
  assert.equal(result.sector_adjusted_alpha_pct, 1.5);
});

test('completes due outcomes and defers unavailable prices', async () => {
  const completed = [];
  const repository = {
    listDue: async () => [
      { id: 'a', direction: 'positive', price_at_signal: 100, nifty_at_signal: 100, sector_at_signal: 100 },
      { id: 'b', direction: 'positive', price_at_signal: 100, nifty_at_signal: 100, sector_at_signal: 100 },
    ],
    complete: async (id, result) => completed.push([id, result]),
  };
  const priceProvider = { getOutcomePrices: async (row) => row.id === 'a' ? { futurePrice: 101, futureNifty: 100.2, futureSector: 100.4 } : null };
  const summary = await processDueOutcomes({ repository, priceProvider, now: new Date('2026-08-10T06:00:00Z') });
  assert.deepEqual(summary, { due: 2, completed: 1, deferred: 1, failed: 0 });
  assert.equal(completed[0][1].status, 'completed');
});
