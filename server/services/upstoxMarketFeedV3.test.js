import assert from 'node:assert/strict';
import test from 'node:test';
import {
  SynchronizedSnapshotStore,
  decodeMarketFeedMessage,
  loadFeedResponseType,
  normalizeFeedResponse,
  resolveFeedHandshake,
  UpstoxMarketFeedV3,
} from './upstoxMarketFeedV3.js';

process.env.UPSTOX_ACCESS_TOKEN ||= 'test-access-token-with-enough-length-abcdefgh';

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
  assert.equal(result.snapshots[0].source, 'upstox');
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

test('uses exchange time for freshness and rejects future or out-of-order ticks', () => {
  const store = new SynchronizedSnapshotStore({ staleAfterMs: 15_000, futureToleranceMs: 5_000 });
  const received = '2026-08-09T08:00:10Z';
  const accepted = store.ingest({ snapshots: [{
    instrument_key: 'NSE_EQ|TEST', received_at: received,
    exchange_timestamp: Date.parse('2026-08-09T08:00:09Z'), ltp: 100,
  }] });
  assert.equal(accepted.accepted, 1);
  assert.equal(store.get('NSE_EQ|TEST').timestamp_source, 'exchange');
  assert.equal(store.quality('NSE_EQ|TEST', { now: new Date('2026-08-09T08:00:20Z') }).pass, true);
  assert.equal(store.quality('NSE_EQ|TEST', { now: new Date('2026-08-09T08:00:30Z') }).reason_codes[0], 'STALE_LIVE_QUOTE');

  store.ingest({ snapshots: [{
    instrument_key: 'NSE_EQ|TEST', received_at: received,
    exchange_timestamp: Date.parse('2026-08-09T08:01:00Z'), ltp: 101,
  }] });
  store.ingest({ snapshots: [{
    instrument_key: 'NSE_EQ|TEST', received_at: '2026-08-09T08:00:12Z',
    exchange_timestamp: Date.parse('2026-08-09T08:00:01Z'), ltp: 99,
  }] });
  const stats = store.stats();
  assert.equal(stats.rejected_future, 1);
  assert.equal(stats.rejected_out_of_order, 1);
  assert.equal(store.get('NSE_EQ|TEST').ltp, 100);
});

test('redirect handshake uses market-data-feed URL with Bearer headers', async () => {
  const previousToken = process.env.UPSTOX_ACCESS_TOKEN;
  process.env.UPSTOX_ACCESS_TOKEN = 'analytics-access-token-with-enough-length-abcdefgh';
  try {
    const handshake = await resolveFeedHandshake({ connectMode: 'redirect' });
    assert.equal(handshake.mode, 'redirect');
    assert.match(handshake.url, /market-data-feed/);
    assert.equal(handshake.headers.Accept, '*/*');
    assert.equal(handshake.headers.Authorization, `Bearer ${process.env.UPSTOX_ACCESS_TOKEN}`);
  } finally {
    if (previousToken === undefined) delete process.env.UPSTOX_ACCESS_TOKEN;
    else process.env.UPSTOX_ACCESS_TOKEN = previousToken;
  }
});

test('authorize handshake omits Bearer because code is in the one-time URL', async () => {
  const handshake = await resolveFeedHandshake({
    connectMode: 'authorize',
    authorize: async () => 'wss://feed.example/once?code=abc',
  });
  assert.equal(handshake.mode, 'authorize');
  assert.equal(handshake.url, 'wss://feed.example/once?code=abc');
  assert.equal(handshake.headers.Accept, '*/*');
  assert.equal(handshake.headers.Authorization, undefined);
});

test('subscribes in binary and normalizes incoming batches', async () => {
  const handlers = {};
  const sent = [];
  const socket = { on: (event, handler) => { handlers[event] = handler; }, send: (value) => sent.push(value), close: () => {} };
  const batches = [];
  const feed = new UpstoxMarketFeedV3({
    instrumentKeys: ['NSE_EQ|TEST'],
    connectMode: 'authorize',
    authorize: async () => 'wss://feed.example/test',
    websocketFactory: () => socket,
    decoder: async () => ({ type: 'live_feed', currentTs: '1786250000000', feeds: { 'NSE_EQ|TEST': { ltpc: { ltp: 100, ltt: '1786250000000', cp: 99 } } } }),
    onBatch: async (batch) => batches.push(batch),
    reconnect: false,
  });
  await feed.start();
  handlers.open();
  assert.ok(Buffer.isBuffer(sent[0]));
  assert.equal(JSON.parse(sent[0].toString()).data.mode, 'full');
  await handlers.message(Buffer.from('binary'));
  assert.equal(batches[0].snapshots[0].ltp, 100);
  assert.equal(feed.status().research_only, true);
  assert.equal(feed.status().provider, 'upstox');
  feed.stop();
});

test('redirect mode sends documented Authorization headers on the WebSocket handshake', async () => {
  const previousToken = process.env.UPSTOX_ACCESS_TOKEN;
  process.env.UPSTOX_ACCESS_TOKEN = 'analytics-access-token-with-enough-length-abcdefgh';
  let handshake;
  const socket = { on: () => {}, send: () => {}, close: () => {} };
  try {
    const feed = new UpstoxMarketFeedV3({
      instrumentKeys: ['NSE_EQ|TEST'],
      connectMode: 'redirect',
      websocketFactory: (url, headers) => { handshake = { url, headers }; return socket; },
      reconnect: false,
    });
    await feed.start();
    assert.match(handshake.url, /market-data-feed/);
    assert.equal(handshake.headers.Accept, '*/*');
    assert.equal(handshake.headers.Authorization, `Bearer ${process.env.UPSTOX_ACCESS_TOKEN}`);
    feed.stop();
  } finally {
    if (previousToken === undefined) delete process.env.UPSTOX_ACCESS_TOKEN;
    else process.env.UPSTOX_ACCESS_TOKEN = previousToken;
  }
});

test('enforces the documented full-mode subscription ceiling', () => {
  const keys = Array.from({ length: 1501 }, (_, index) => `NSE_EQ|${index}`);
  assert.throws(() => new UpstoxMarketFeedV3({ instrumentKeys: keys }), /1500/);
});

test('on 403, switches from redirect to authorize and retries with a fresh URL', async () => {
  const sockets = [];
  let authorizations = 0;
  const feed = new UpstoxMarketFeedV3({
    instrumentKeys: ['NSE_EQ|TEST'],
    connectMode: 'redirect',
    authorize: async () => `wss://feed.example/${++authorizations}`,
    websocketFactory: (url, headers) => {
      const handlers = {};
      const socket = {
        url,
        headers,
        on: (event, handler) => { handlers[event] = handler; },
        send: () => {},
        close: () => {},
      };
      sockets.push({ socket, handlers });
      return socket;
    },
    reconnectBaseMs: 1,
    random: () => 0,
  });

  await feed.start();
  assert.match(sockets[0].socket.url, /market-data-feed/);
  assert.ok(sockets[0].socket.headers.Authorization);

  sockets[0].handlers.error(new Error('Unexpected server response: 403'));
  sockets[0].handlers.close();
  assert.equal(feed.status().status, 'reconnecting');
  assert.equal(feed.status().reconnects, 1);

  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(authorizations, 1);
  assert.equal(sockets.length, 2);
  assert.match(sockets[1].socket.url, /feed\.example\/1/);
  assert.equal(sockets[1].socket.headers.Authorization, undefined);
  sockets[1].handlers.open();
  assert.equal(feed.status().status, 'connected');
  assert.equal(feed.status().last_error, null);
  feed.stop();
});
