import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizedObservations } from './liveAlphaBaselineBootstrap.js';

test('turns per-minute candle volume into point-in-time cumulative observations', () => {
  const rows = normalizedObservations('NSE_EQ|A', { data: { candles: [
    ['2026-08-07T03:46:00.000Z', 1, 1, 1, 1, 20],
    ['2026-08-07T03:45:00.000Z', 1, 1, 1, 1, 10],
  ] } });
  assert.deepEqual(rows.map((row) => row.cumulative_volume), [10, 30]);
  assert.ok(rows.every((row) => row.instrument_key === 'NSE_EQ|A'));
});
