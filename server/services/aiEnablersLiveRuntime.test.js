import test from 'node:test';
import assert from 'node:assert/strict';
import { AiEnablersLiveRuntime, snapshotFrom } from './aiEnablersLiveRuntime.js';
import { LastGoodPrices } from './aiEnablersQuotes.js';

const NOW = Date.parse('2026-09-17T06:52:30Z');   // 12:22:30 IST, half the session

const UNIVERSE = {
  benchmarkKey: 'NSE_INDEX|Nifty 50',
  members: [
    { symbol: 'AAA', instrumentKey: 'NSE_EQ|INE000A01001', layer: 'power', subLayers: ['equipment'] },
    { symbol: 'BBB', instrumentKey: 'NSE_EQ|INE000A01002', layer: 'data_centre', subLayers: ['hardware'] },
  ],
};

const tick = (ltp, previousClose, atMs, volume = null) => ({
  ltp, previous_close: previousClose, cumulative_volume: volume,
  effective_timestamp: new Date(atMs).toISOString(),
});

const storeOf = (rows) => ({ get: (key) => rows[key] || null, stats: () => ({}) });

const fullStore = storeOf({
  'NSE_EQ|INE000A01001': tick(110, 100, NOW - 1_000, 500_000),
  'NSE_EQ|INE000A01002': tick(90, 100, NOW - 1_000, 2_000_000),
  'NSE_INDEX|Nifty 50': tick(25_250, 25_000, NOW - 1_000),
});

const runtimeWith = (store, extra = {}) => new AiEnablersLiveRuntime({
  universe: UNIVERSE, store, lastGood: new LastGoodPrices(), now: () => NOW, ...extra,
});

test('the basket reports return, breadth, contribution and relative return', () => {
  const snapshot = runtimeWith(fullStore).current();
  assert.equal(snapshot.status, 'ok');
  // +10% and -10%, equal weighted.
  assert.equal(snapshot.index.return_pp, 0);
  assert.deepEqual(
    { advancing: snapshot.index.breadth.advancing, declining: snapshot.index.breadth.declining },
    { advancing: 1, declining: 1 },
  );
  // Nifty +1%, basket flat, so the basket lagged by a point.
  assert.equal(snapshot.index.relative.benchmark_return_pp, 1);
  assert.equal(snapshot.index.relative.excess_pp, -1);
  const contributions = Object.fromEntries(
    snapshot.index.contributions.byName.map((one) => [one.symbol, one.contribution_pp]),
  );
  assert.deepEqual(contributions, { AAA: 5, BBB: -5 });
});

test('layer and sub-layer returns are reported and reconcile', () => {
  const snapshot = runtimeWith(fullStore).current();
  const byLayer = Object.fromEntries(
    snapshot.index.contributions.byLayer.map((one) => [one.layer, one.contribution_pp]),
  );
  assert.deepEqual(byLayer, { power: 5, data_centre: -5 });
  assert.equal(snapshot.index.residual_ok, true);
  assert.equal(snapshot.index.subLayerResidual_ok, true);
  assert.deepEqual(snapshot.index.unclassified, []);
});

test('the volume ratio reaches the snapshot, time-adjusted', () => {
  const snapshot = runtimeWith(fullStore, {
    volumeBaselines: { AAA: 1_000_000, BBB: 1_000_000 },
  }).current();
  // Half the session gone: 500k against a 1M day is normal, 2M is four times.
  assert.equal(snapshot.volumes.AAA.ratio, 1);
  assert.equal(snapshot.volumes.BBB.ratio, 4);
});

test('a member with no volume baseline says so rather than reporting zero', () => {
  const snapshot = runtimeWith(fullStore).current();
  assert.equal(snapshot.volumes.AAA.ratio, null);
  assert.equal(snapshot.volumes.AAA.reason, 'NO_BASELINE');
});

test('the basket stays in refusal below the coverage floor', () => {
  // One of two members priced is 50%, under the 80% floor.
  const half = storeOf({
    'NSE_EQ|INE000A01001': tick(110, 100, NOW - 1_000),
    'NSE_INDEX|Nifty 50': tick(25_250, 25_000, NOW - 1_000),
  });
  const snapshot = runtimeWith(half).current();
  assert.equal(snapshot.status, 'insufficient_coverage');
  assert.equal(snapshot.index.level, null);
  assert.equal(snapshot.index.return_pct, null);
  assert.match(snapshot.index.reason, /1 of 2 members priced/);
});

test('a snapshot records how much of the basket was actually live', () => {
  const lastGood = new LastGoodPrices();
  lastGood.remember('NSE_EQ|INE000A01002', { ltp: 90, previousClose: 100, at: NOW - 90_000 });
  const stale = storeOf({
    'NSE_EQ|INE000A01001': tick(110, 100, NOW - 1_000),
    'NSE_EQ|INE000A01002': tick(90, 100, NOW - 200_000),
    'NSE_INDEX|Nifty 50': tick(25_250, 25_000, NOW - 1_000),
  });
  const runtime = new AiEnablersLiveRuntime({
    universe: UNIVERSE, store: stale, lastGood, now: () => NOW,
  });
  const snapshot = runtime.current();
  // It still computes - one stale name out of two is within the coverage
  // floor once the fallback covers it - but it must not claim to be live.
  assert.equal(snapshot.status, 'ok');
  assert.deepEqual(
    { live: snapshot.quality.live, lastGood: snapshot.quality.last_good },
    { live: 1, lastGood: 1 },
  );
  assert.equal(snapshot.quality.live_share, 0.5);
});

test('refusals are retained in history, not skipped', () => {
  // A history that only holds the computable minutes cannot answer "was the
  // feed up at 11:04?", which is the first question asked of a bad level.
  const runtime = runtimeWith(storeOf({}));
  runtime.tick();
  runtime.tick();
  assert.equal(runtime.history().length, 2);
  assert.equal(runtime.history()[0].status, 'insufficient_coverage');
});

test('history is bounded, so a long session does not grow without limit', () => {
  const runtime = runtimeWith(fullStore, { retention: 3 });
  for (let i = 0; i < 10; i += 1) runtime.tick();
  assert.equal(runtime.history().length, 3);
});

test('a member that cannot be keyed is named in status, not dropped in silence', () => {
  const runtime = new AiEnablersLiveRuntime({
    universe: { benchmarkKey: 'NSE_INDEX|Nifty 50', members: [
      { symbol: 'AAA', instrumentKey: 'NSE_EQ|INE000A01001', layer: 'power', subLayers: ['equipment'] },
      { symbol: 'GHOST', layer: 'power', subLayers: ['equipment'] },
    ] },
    store: fullStore, lastGood: new LastGoodPrices(), now: () => NOW,
  });
  assert.deepEqual(runtime.status().unresolved, [{ symbol: 'GHOST', reason: 'NO_ISIN' }]);
  assert.deepEqual(runtime.current().quality.unresolved, [{ symbol: 'GHOST', reason: 'NO_ISIN' }]);
});

test('the benchmark is subscribed alongside the members', () => {
  const runtime = runtimeWith(fullStore);
  assert.equal(runtime.status().subscribed, 3);
  assert.equal(runtime.status().benchmarkKey, 'NSE_INDEX|Nifty 50');
});

test('relative return is null when the benchmark is not priced', () => {
  const noBenchmark = storeOf({
    'NSE_EQ|INE000A01001': tick(110, 100, NOW - 1_000),
    'NSE_EQ|INE000A01002': tick(90, 100, NOW - 1_000),
  });
  const snapshot = runtimeWith(noBenchmark).current();
  assert.equal(snapshot.status, 'ok');
  assert.equal(snapshot.index.relative, null);
});

test('snapshotFrom needs no runtime, so the page can recompute from a book', () => {
  const book = {
    quotes: { AAA: { ltp: 110, previousClose: 100, at: NOW }, BBB: { ltp: 90, previousClose: 100, at: NOW } },
    benchmark: { ltp: 25_250, previousClose: 25_000, at: NOW, source: 'live' },
    sources: { live: ['AAA', 'BBB'], last_good: [], missing: [] },
    unresolved: [],
    volumes: {},
  };
  const snapshot = snapshotFrom(UNIVERSE, book, { now: NOW });
  assert.equal(snapshot.index.return_pp, 0);
  assert.equal(snapshot.index.relative.excess_pp, -1);
});
