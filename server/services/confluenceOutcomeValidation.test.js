import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateConfluenceOutcome, confluenceHorizonDueAt, createConfluenceOutcomeSchedule, summarizeConfluenceOutcomes } from './confluenceOutcomeValidation.js';

test('creates all eight confluence validation horizons', () => {
  assert.deepEqual(createConfluenceOutcomeSchedule('event-1', '2026-08-10T05:50:00Z').map((row) => row.horizon), ['5m','15m','30m','60m','close','1d','5d','20d']);
  assert.equal(confluenceHorizonDueAt('2026-08-14T06:00:00Z', '1d'), '2026-08-17T10:00:00.000Z');
});

test('calculates benchmark and sector adjusted excess return', () => {
  const result = calculateConfluenceOutcome({ priceAtSignal: 100, futurePrice: 103, benchmarkAtSignal: 100, futureBenchmark: 101, sectorAtSignal: 100, futureSector: 101.5 });
  assert.equal(result.excess_return_pct, 2);
  assert.equal(result.sector_adjusted_alpha_pct, 1.5);
  assert.equal(result.positive_excess, true);
});

test('aggregates classifications by horizon and regime without claiming early calibration', () => {
  const rows = [{ status: 'completed', classification: 'HIGH_CONFLUENCE', horizon: '5d', market_regime: 'TREND_UP', excess_return_pct: 2, sector_adjusted_alpha_pct: 1.5 }, { status: 'completed', classification: 'HIGH_CONFLUENCE', horizon: '5d', market_regime: 'TREND_UP', excess_return_pct: -1, sector_adjusted_alpha_pct: -0.5 }];
  const [summary] = summarizeConfluenceOutcomes(rows);
  assert.equal(summary.observations, 2);
  assert.equal(summary.positive_alpha_rate, 50);
  assert.equal(summary.average_excess_return_pct, 0.5);
  assert.equal(summary.calibrated, false);
});
