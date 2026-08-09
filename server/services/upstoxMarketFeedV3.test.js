import assert from 'node:assert/strict';
import test from 'node:test';
import { SynchronizedSnapshotStore, decodeMarketFeedMessage, loadFeedResponseType, normalizeFeedResponse, UpstoxMarketFeedV3 } from './upstoxMarketFeedV3.js';

test('decodes the official V3 protobuf contract', async () => {
  const type = await loadFeedResponseType();
  const encoded = type.encode(type.create({
    type: 1, currentTs: '1786250000000', feeds: {
      'NSE_EQ|TEST': { fullFeed: { marketFF: { ltpc: { ltp: 101.5, ltt: '1786249999000', ltq: '25', cp: 100 }, atp: 100.7, vtt: '250000', oi: 1200, marketLevel: { bidAskQuote: [{ bidP: 101.45, askP: 101.55 }] } } } },
    },
  })).finish();
  const decoded = await decodeMarketFeedMessage(encoded);
  const result = normalizeFeedResponse(decoded, new Date('2026-08-09T08:00:00Z'));
  assert.equal(result.snapshots[0].instrument_key, 'NSE_EQ|TEST');
  assert.equal(result.snapshots[0].ltp, 101.5);
  assert.equal(result.snapshots[0].cumulative_volume, 250000);
  assert.ok(result.snapshots[0].spread_bps > 0);
});

test('requires complete, fresh and low-skew snapshots', () => {
  const store = new SynchronizedSnapshotStore({ staleAfterMs: 15_000 });
  store.ingest({ snapshots: [
    { instrument_key: 'A|1', received_at: '2026-08-09T08:00:00Z' },
    { instrument_key: 'A|2', received_at: '2026-08-09T08:00:02Z' },
  ] });
  assert.equal(store.synchronized(['A|1', 'A|2'], { now: new Date('2026-08-09T08:00:05Z') }).ready, true);
  assert.equal(store.synchronized(['A|1', 'A|2'], { now: new Date('2026-08-09T08:00:20Z') }).ready, false);
  assert.equal(store.synchronized(['A|1', 'A|3'], { now: new Date('2026-08-09T08:00:05Z') }).ready, false);
});

test('subscribes in binary and normalizes incoming batches', async () => {
  const handlers = {};
  const sent = [];
  const socket = { on: (event, handler) => { handlers[event] = handler; }, send: (value) => sent.push(value), close: () => {} };
  const batches = [];
  const feed = new UpstoxMarketFeedV3({
    instrumentKeys: ['NSE_EQ|TEST'], authorize: async () => 'wss://feed.example/test', websocketFactory: () => socket,
    decoder: async () => ({ type: 'live_feed', currentTs: '1786250000000', feeds: { 'NSE_EQ|TEST': { ltpc: { ltp: 100, ltt: '1786250000000', cp: 99 } } } }),
    onBatch: async (batch) => batches.push(batch), reconnect: false,
  });
  await feed.start();
  handlers.open();
  assert.ok(Buffer.isBuffer(sent[0]));
  assert.equal(JSON.parse(sent[0].toString()).data.mode, 'full');
  await handlers.message(Buffer.from('binary'));
  assert.equal(batches[0].snapshots[0].ltp, 100);
  assert.equal(feed.status().research_only, true);
  feed.stop();
});

test('enforces the documented full-mode subscription ceiling', () => {
  const keys = Array.from({ length: 1501 }, (_, index) => `NSE_EQ|${index}`);
  assert.throws(() => new UpstoxMarketFeedV3({ instrumentKeys: keys }), /1500/);
});
