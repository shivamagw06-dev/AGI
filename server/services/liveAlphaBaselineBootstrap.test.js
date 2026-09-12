import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizedObservations } from './liveAlphaBaselineBootstrap.js';
import { VolumeBaselineIndex } from './minuteVolumeBaseline.js';

test('turns per-minute candle volume into point-in-time cumulative observations', () => {
  const rows = normalizedObservations('NSE_EQ|A', { data: { candles: [
    ['2026-08-07T03:46:00.000Z', 1, 1, 1, 1, 20],
    ['2026-08-07T03:45:00.000Z', 1, 1, 1, 1, 10],
  ] } });
  assert.deepEqual(rows.map((row) => row.cumulative_volume), [10, 30]);
  assert.ok(rows.every((row) => row.instrument_key === 'NSE_EQ|A'));
});

test('counts baseline coverage by instrument rather than row volume', () => {
  const index = new VolumeBaselineIndex([
    { instrument_key: 'NSE_EQ|A', minute_of_session: 0, expected_cumulative_volume: 10 },
    { instrument_key: 'NSE_EQ|A', minute_of_session: 1, expected_cumulative_volume: 20 },
    { instrument_key: 'NSE_EQ|B', minute_of_session: 0, expected_cumulative_volume: 30 },
  ]);
  assert.equal(index.values.size, 3);
  assert.equal(index.instrumentCount(), 2);
  assert.equal(index.hasInstrument('NSE_EQ|A'), true);
  assert.equal(index.hasInstrument('NSE_EQ|C'), false);
});
