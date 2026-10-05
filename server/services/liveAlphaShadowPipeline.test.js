import assert from 'node:assert/strict';
import test from 'node:test';
import { buildMinuteVolumeBaselines, VolumeBaselineIndex } from './minuteVolumeBaseline.js';
import { IntradayFeatureStore, MomentumShadowPipeline } from './liveAlphaShadowPipeline.js';

test('builds median minute baselines using prior sessions only', () => {
  const rows = [];
  for (let day = 1; day <= 6; day += 1) rows.push({ instrument_key: 'NSE_EQ|A', observed_at: `2026-08-0${day}T04:00:00Z`, cumulative_volume: day * 100 });
  const baseline = buildMinuteVolumeBaselines(rows, { minimumSessions: 5, throughSession: '2026-08-07' });
  assert.equal(baseline[0].instrument_key, 'NSE_EQ|A');
  assert.equal(baseline[0].minute_of_session, 15);
  assert.equal(baseline[0].expected_cumulative_volume, 350);
  assert.equal(baseline[0].sample_sessions, 6);
});

test('does not invent intraday history from previous close', () => {
  const store = new IntradayFeatureStore();
  store.ingest({ snapshots: [{
    instrument_key: 'NSE_INDEX|Nifty 50',
    received_at: '2026-08-25T06:00:00Z',
    ltp: 24178.85,
    previous_close: 24219.0,
  }] });
  const result = store.returns('NSE_INDEX|Nifty 50', Date.parse('2026-08-25T06:00:00Z'));
  assert.equal(result.return15m, null);
  assert.equal(result.return60m, null);
});

test('incomplete current candle cannot replace missing lookback history', () => {
  const store = new IntradayFeatureStore();
  const at = Date.parse('2026-08-25T09:00:00Z');
  store.ingest({ snapshots: [{
    instrument_key: 'NSE_INDEX|Nifty 50',
    received_at: '2026-08-25T09:00:00Z',
    ltp: 24178.85,
    previous_close: 24219.0,
    ohlc: [{ interval: 'I1', close: 24178.85, high: 24180, low: 24170, timestamp: at }],
  }] });
  const result = store.returns('NSE_INDEX|Nifty 50', at);
  assert.equal(result.return15m, null);
  assert.equal(result.return60m, null);
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

test('retains the latest genuine cumulative-volume tick behind an OHLC point', () => {
  const store = new IntradayFeatureStore();
  store.ingest({ snapshots: [
    { instrument_key: 'A', received_at: '2026-08-14T06:00:00Z', ltp: 100, cumulative_volume: 2500 },
    { instrument_key: 'A', received_at: '2026-08-14T06:01:00Z', ltp: 101, cumulative_volume: null, source: 'upstox_ohlc_1m' },
  ] });
  assert.equal(store.latest('A').ltp, 101);
  assert.equal(store.latestWithFinite('A', 'cumulative_volume').cumulative_volume, 2500);
});

test('restores opening range and 15m returns from Upstox 1m OHLC after reconnect', () => {
  const store = new IntradayFeatureStore();
  // 09:15–09:29 IST = 03:45–03:59 UTC on this date
  const open = Date.parse('2026-08-11T03:45:00Z');
  const bars = Array.from({ length: 15 }, (_, index) => ({
    interval: 'I1',
    open: 100,
    high: 101 + index * 0.1,
    low: 99.5,
    close: 100.5 + index * 0.05,
    volume: 1000 + index,
    timestamp: open + index * 60_000,
  }));
  store.ingest({
    snapshots: [{
      instrument_key: 'NSE_EQ|TEST',
      received_at: '2026-08-11T05:00:00Z',
      ltp: 103,
      ohlc: bars,
    }],
  });
  const range = store.openingRange('NSE_EQ|TEST', new Date('2026-08-11T05:00:00Z'));
  assert.ok(range);
  assert.equal(Number(range.high.toFixed(2)), 102.4);
  assert.equal(range.low, 99.5);
  const returns = store.returns('NSE_EQ|TEST', Date.parse('2026-08-11T05:00:00Z'));
  assert.equal(returns.return15m, null); // opening bars are too old for this horizon
  assert.ok(returns.return60m !== null);
});

test('runs momentum in shadow mode once a bucket has complete features', async () => {
  const universe = Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, sector: 'BANK', instrumentKey: `EQ|${index}`, sectorInstrumentKey: 'INDEX|BANK' }));
  const baselines = new VolumeBaselineIndex(universe.map((row) => ({ instrument_key: row.instrumentKey, minute_of_session: 120, expected_cumulative_volume: 1000 })));
  const saved = [];
  const volumeSaved = [];
  const openingSaved = [];
  const meanReversionSaved = [];
  const pipeline = new MomentumShadowPipeline({ universe, benchmarkKey: 'INDEX|NIFTY', baselineIndex: baselines, repository: { saveMomentumRun: async (run) => saved.push(run), saveVolumeAnomalyRun: async (run) => volumeSaved.push(run), saveOpeningRangeRun: async (run) => openingSaved.push(run), saveMeanReversionRun: async (run) => meanReversionSaved.push(run) } });
  for (const time of [...Array.from({ length: 15 }, (_, i) => new Date(Date.parse('2026-08-10T03:45:00Z') + i * 60_000).toISOString()), '2026-08-10T04:45:00Z', '2026-08-10T05:30:00Z', '2026-08-10T05:45:00Z']) {
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
  assert.equal(volumeSaved.length, 1);
  assert.equal(openingSaved.length, 1);
  assert.equal(meanReversionSaved.length, 1);
  assert.equal(result.companion_engines[0].engine, 'volume_liquidity_anomaly_v1');
  assert.equal(result.companion_engines[1].engine, 'opening_range_expansion_v1');
  assert.equal(result.companion_engines[2].engine, 'intraday_mean_reversion_v1');
  assert.equal(result.derivatives_status, 'derivative_instruments_not_configured');
  assert.deepEqual(result.persistence.map((row) => row.status), ['stored', 'stored', 'stored', 'stored', 'unavailable']);
  assert.equal((await pipeline.evaluate(new Date('2026-08-10T05:45:30Z'))).reason, 'already_evaluated_bucket');
});

test('one engine storage failure does not block the remaining engines', async () => {
  const stored = [];
  const pipeline = new MomentumShadowPipeline({
    repository: {
      saveMomentumRun: async () => { stored.push('momentum'); return { signals: 10 }; },
      saveOpeningRangeRun: async () => { throw new Error('opening write failed'); },
      saveMeanReversionRun: async () => { stored.push('mean'); return { signals: 10 }; },
    },
  });
  const statuses = await pipeline.persistEngines([
    { engine: 'momentum', method: 'saveMomentumRun', result: {} },
    { engine: 'opening', method: 'saveOpeningRangeRun', result: {} },
    { engine: 'mean', method: 'saveMeanReversionRun', result: {} },
    { engine: 'derivatives', method: 'saveDerivativesRun', result: null, reason: 'derivative_instruments_not_configured' },
  ], {});
  assert.deepEqual(stored, ['momentum', 'mean']);
  assert.deepEqual(statuses.map((row) => row.status), ['stored', 'failed', 'stored', 'unavailable']);
  assert.equal(statuses[1].error, 'opening write failed');
  assert.equal(statuses[3].reason, 'derivative_instruments_not_configured');
});

test('recovers a complete opening range older than rolling retention, rejects gaps and other sessions', () => {
  const store = new IntradayFeatureStore();
  const now = new Date('2026-10-05T07:00:00Z');
  const start = Date.parse('2026-10-05T03:45:00Z');
  const bars = Array.from({ length: 15 }, (_, i) => ({ interval: 'I1', timestamp: start + i * 60_000, high: 110, low: 90, close: 100 }));
  store.ingestCandles('A', bars.slice(1), now);
  assert.equal(store.openingRange('A', now), null);
  store.ingestCandles('A', bars.slice(0, 1), now);
  assert.equal(store.openingRange('A', now).high, 110);
  assert.equal(store.latest('A'), null);
  store.ingestCandles('B', bars.map(b => ({ ...b, timestamp: b.timestamp - 86400000 })), now);
  assert.equal(store.openingRange('B', now), null);
});

test('completed historical futures candles recover actual OI changes without using future candles', () => {
  const store = new IntradayFeatureStore();
  const now = new Date('2026-10-05T07:00:00Z');
  store.ingestCandles('F', [
    { interval: 'I1', timestamp: Date.parse('2026-10-05T06:44:00Z'), close: 100, open_interest: 1000 },
    { interval: 'I1', timestamp: Date.parse('2026-10-05T07:00:00Z'), close: 999, open_interest: 9000 },
  ], now);
  store.ingest({ snapshots: [{ instrument_key: 'F', received_at: now.toISOString(), ltp: 101, open_interest: 1100 }] });
  const result = store.derivatives('F', now.getTime());
  assert.ok(Math.abs(result.priceReturn15m - 1) < 1e-9);
  assert.ok(Math.abs(result.oiChange15m - 10) < 1e-9);
  assert.equal(store.returns('F', now.getTime()).return60m, null);
  assert.equal(store.returns('F', now.getTime() + 180000), null);
});

test('all five engines evaluate genuine history; mapped futures with missing OI report warmup', async () => {
  const now = new Date('2026-10-05T05:45:00Z');
  const universe = Array.from({ length: 10 }, (_, i) => ({ symbol: `S${i}`, sector: 'BANK', instrumentKey: `EQ|${i}`, sectorInstrumentKey: 'INDEX', derivativeInstrumentKey: `FUT|${i}` }));
  const repository = Object.fromEntries(['saveMomentumRun','saveVolumeAnomalyRun','saveOpeningRangeRun','saveMeanReversionRun','saveDerivativesRun'].map(k => [k, async r => ({signals:r.signals.length})]));
  const store = new IntradayFeatureStore();
  const baselineIndex = new VolumeBaselineIndex(universe.map(m => ({ instrument_key: m.instrumentKey, minute_of_session: 120, expected_cumulative_volume: 1000 })));
  const pipeline = new MomentumShadowPipeline({ universe, benchmarkKey: 'INDEX', featureStore: store, baselineIndex, repository });
  for (let minute = 0; minute <= 120; minute++) {
    const received_at = new Date(now.getTime() - (120 - minute) * 60000).toISOString();
    store.ingest({ snapshots: ['INDEX', ...universe.map(m=>m.instrumentKey)].map((instrument_key,i)=>({instrument_key,received_at,ltp:100 + minute*(i+1)/100, cumulative_volume:1500,spread_bps:5})) });
  }
  const warmup = await pipeline.evaluate(now);
  assert.equal(warmup.derivatives_status, 'derivative_history_warming_or_incomplete:0/10');
  for (const minute of [15,0]) store.ingest({snapshots:universe.map(m=>({instrument_key:m.derivativeInstrumentKey,received_at:new Date(now.getTime()-minute*60000).toISOString(),ltp:minute?100:102,open_interest:minute?1000:1100,spread_bps:5}))});
  const independentPipeline = new MomentumShadowPipeline({ universe, benchmarkKey:'INDEX', featureStore:store, baselineIndex, repository });
  const result = await independentPipeline.evaluate(now);
  assert.equal(result.persistence.length,5);
  assert.ok(result.persistence.every(p=>p.status==='stored'));
  assert.equal(result.execution_enabled,false);
});
