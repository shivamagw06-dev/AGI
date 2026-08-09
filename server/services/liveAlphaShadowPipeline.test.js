import assert from 'node:assert/strict';
import test from 'node:test';
import { buildMinuteVolumeBaselines, VolumeBaselineIndex } from './minuteVolumeBaseline.js';
import { IntradayFeatureStore, MomentumShadowPipeline } from './liveAlphaShadowPipeline.js';

test('builds median minute baselines using prior sessions only', () => {
  const rows = [];
  for (let day = 1; day <= 6; day += 1) rows.push({ instrument_key: 'NSE_EQ|A', observed_at: `2026-08-0${day}T04:00:00Z`, cumulative_volume: day * 100 });
  const baseline = buildMinuteVolumeBaselines(rows, { minimumSessions: 5, throughSession: '2026-08-07' });
  assert.equal(baseline[0].expected_cumulative_volume, 350);
  assert.equal(baseline[0].sample_sessions, 6);
});

test('retains rolling observations and calculates returns', () => {
  const store = new IntradayFeatureStore();
  store.ingest({ snapshots: [
    { instrument_key: 'A', received_at: '2026-08-09T04:00:00Z', ltp: 100 },
    { instrument_key: 'A', received_at: '2026-08-09T04:15:00Z', ltp: 102 },
    { instrument_key: 'A', received_at: '2026-08-09T05:00:00Z', ltp: 105 },
  ] });
  const result = store.returns('A', Date.parse('2026-08-09T05:00:00Z'));
  assert.equal(Number(result.return60m.toFixed(2)), 5);
});

test('runs momentum in shadow mode once a bucket has complete features', async () => {
  const universe = Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, sector: 'BANK', instrumentKey: `EQ|${index}`, sectorInstrumentKey: 'INDEX|BANK' }));
  const baselines = new VolumeBaselineIndex(universe.map((row) => ({ instrument_key: row.instrumentKey, minute_of_session: 120, expected_cumulative_volume: 1000 })));
  const saved = [];
  const pipeline = new MomentumShadowPipeline({ universe, benchmarkKey: 'INDEX|NIFTY', baselineIndex: baselines, repository: { saveMomentumRun: async (run) => saved.push(run) } });
  for (const time of ['2026-08-10T04:45:00Z', '2026-08-10T05:30:00Z', '2026-08-10T05:45:00Z']) {
    const step = time.endsWith('04:45:00Z') ? 0 : time.endsWith('05:30:00Z') ? 1 : 2;
    pipeline.ingest({ snapshots: [
      { instrument_key: 'INDEX|NIFTY', received_at: time, ltp: 100 + step },
      { instrument_key: 'INDEX|BANK', received_at: time, ltp: 100 + step * 1.2 },
      ...universe.map((row, index) => ({ instrument_key: row.instrumentKey, received_at: time, ltp: 100 + step * (1 + index / 20), cumulative_volume: 1200 + index * 50, spread_bps: 5 })),
    ] });
  }
  const result = await pipeline.evaluate(new Date('2026-08-10T05:45:00Z'));
  assert.equal(result.execution_enabled, false);
  assert.equal(saved.length, 1);
  assert.equal((await pipeline.evaluate(new Date('2026-08-10T05:45:30Z'))).reason, 'already_evaluated_bucket');
});
