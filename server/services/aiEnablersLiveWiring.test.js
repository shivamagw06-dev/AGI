import test from 'node:test';
import assert from 'node:assert/strict';
import { SynchronizedSnapshotStore, normalizeFeedResponse } from './upstoxMarketFeedV3.js';
import { AiEnablersLiveRuntime } from './aiEnablersLiveRuntime.js';
import { LastGoodPrices } from './aiEnablersQuotes.js';

/**
 * End to end over the real store, with messages in the shape
 * normalizeFeedResponse actually produces from the V3 protobuf. The unit
 * tests above use a stub store; this one exists because the seam between the
 * feed's snapshot rows and the index's quotes is where a field-name change
 * would go unnoticed.
 */
const UNIVERSE = {
  benchmarkKey: 'NSE_INDEX|Nifty 50',
  members: [
    { symbol: 'CGPOWER', instrumentKey: 'NSE_EQ|INE067A01029', layer: 'semiconductor', subLayers: ['osat'] },
    { symbol: 'NETWEB', instrumentKey: 'NSE_EQ|INE0NT901020', layer: 'data_centre', subLayers: ['hardware'] },
  ],
};

const feedMessage = (atMs, prices) => ({
  type: 'live_feed',
  currentTs: String(atMs),
  feeds: Object.fromEntries(Object.entries(prices).map(([key, [ltp, cp, vtt]]) => [
    key,
    { fullFeed: { marketFF: { ltpc: { ltp, cp, ltt: String(atMs) }, vtt } } },
  ])),
});

const runtimeOver = (store, now) => new AiEnablersLiveRuntime({
  universe: UNIVERSE, store, lastGood: new LastGoodPrices(), now: () => now,
  volumeBaselines: { CGPOWER: 1_000_000, NETWEB: 1_000_000 },
});

test('a real feed message reaches the basket through the real store', () => {
  const now = Date.parse('2026-09-17T06:52:30Z');
  const store = new SynchronizedSnapshotStore();
  store.ingest(normalizeFeedResponse(feedMessage(now - 1_000, {
    'NSE_EQ|INE067A01029': [110, 100, 500_000],
    'NSE_EQ|INE0NT901020': [95, 100, 1_500_000],
    'NSE_INDEX|Nifty 50': [25_250, 25_000, 0],
  }), new Date(now - 1_000)));

  const snapshot = runtimeOver(store, now).current();
  assert.equal(snapshot.status, 'ok');
  assert.equal(snapshot.index.return_pp, 2.5);          // (+10 - 5) / 2
  assert.equal(snapshot.index.relative.excess_pp, 1.5); // Nifty +1
  assert.equal(snapshot.quality.live, 2);
  assert.equal(snapshot.quality.last_good, 0);
  assert.equal(snapshot.volumes.CGPOWER.ratio, 1);
  assert.equal(snapshot.volumes.NETWEB.ratio, 3);
});

test('the layer breakdown survives the trip and reconciles', () => {
  const now = Date.parse('2026-09-17T06:52:30Z');
  const store = new SynchronizedSnapshotStore();
  store.ingest(normalizeFeedResponse(feedMessage(now - 1_000, {
    'NSE_EQ|INE067A01029': [110, 100, 1],
    'NSE_EQ|INE0NT901020': [95, 100, 1],
    'NSE_INDEX|Nifty 50': [25_250, 25_000, 0],
  }), new Date(now - 1_000)));
  const snapshot = runtimeOver(store, now).current();
  assert.deepEqual(
    Object.fromEntries(snapshot.index.contributions.bySubLayer.map((o) => [o.subLayer, o.contribution_pp])),
    { 'semiconductor/osat': 5, 'data_centre/hardware': -2.5 },
  );
  assert.equal(snapshot.index.subLayerResidual_ok, true);
});

test('when the feed goes quiet the basket rides last-good, then refuses', () => {
  const opened = Date.parse('2026-09-17T06:00:00Z');
  const store = new SynchronizedSnapshotStore();
  const lastGood = new LastGoodPrices();
  const runtime = new AiEnablersLiveRuntime({
    universe: UNIVERSE, store, lastGood, now: () => opened,
  });
  store.ingest(normalizeFeedResponse(feedMessage(opened - 1_000, {
    'NSE_EQ|INE067A01029': [110, 100, 1],
    'NSE_EQ|INE0NT901020': [95, 100, 1],
    'NSE_INDEX|Nifty 50': [25_250, 25_000, 0],
  }), new Date(opened - 1_000)));

  assert.equal(runtime.current().quality.live, 2);

  // Two minutes on, no new tick: the live window has passed, the fallback
  // covers it, and the basket still computes but says it is not live.
  runtime.now = () => opened + 120_000;
  const riding = runtime.current();
  assert.equal(riding.status, 'ok');
  assert.equal(riding.quality.live, 0);
  assert.equal(riding.quality.last_good, 2);
  assert.equal(riding.quality.live_share, 0);

  // Ten minutes on, past the fallback's own bound: coverage collapses and the
  // index refuses rather than quoting a level off a dead feed.
  runtime.now = () => opened + 600_000;
  const dead = runtime.current();
  assert.equal(dead.status, 'insufficient_coverage');
  assert.equal(dead.index.level, null);
});

test('an out-of-order tick is rejected by the store, not averaged in', () => {
  const now = Date.parse('2026-09-17T06:52:30Z');
  const store = new SynchronizedSnapshotStore();
  store.ingest(normalizeFeedResponse(feedMessage(now - 1_000, {
    'NSE_EQ|INE067A01029': [110, 100, 1],
  }), new Date(now - 1_000)));
  // A stale duplicate arriving after a reconnect.
  store.ingest(normalizeFeedResponse(feedMessage(now - 30_000, {
    'NSE_EQ|INE067A01029': [50, 100, 1],
  }), new Date(now - 1_000)));
  assert.equal(store.get('NSE_EQ|INE067A01029').ltp, 110);
});
