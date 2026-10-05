import test from 'node:test';
import assert from 'node:assert/strict';
import { bootstrapLiveAlphaIntraday, normalizeIntradayCandles } from './liveAlphaIntradayBootstrap.js';
import { IntradayFeatureStore } from './liveAlphaShadowPipeline.js';

test('bootstrap restores genuine completed bars and complete opening coverage', async () => {
  const start = Date.parse('2026-10-05T03:45:00Z');
  const candles = Array.from({ length: 15 }, (_, i) => [new Date(start + i * 60000).toISOString(), 100, 110, 90, 101, 25, 1000]);
  const store = new IntradayFeatureStore();
  const result = await bootstrapLiveAlphaIntraday({ instrumentKeys: ['A', 'A'], featureStore: store, delayMs: 0, now: () => new Date('2026-10-05T07:00:00Z'), fetchCandles: async () => ({ data: { candles } }) });
  assert.equal(result.requested, 1);
  assert.equal(result.opening_ranges, 1);
  assert.equal(result.status, 'ready');
  assert.equal(store.latest('A'), null);
  assert.equal(normalizeIntradayCandles({ data: { candles: [['bad', 100, 99, 101, 100]] } }).length, 0);
});

test('authentication or throttling stops further bootstrap requests', async () => {
  let calls = 0;
  const result = await bootstrapLiveAlphaIntraday({ instrumentKeys: ['A','B','C','D'], featureStore: new IntradayFeatureStore(), delayMs: 0, fetchCandles: async () => { calls++; throw Object.assign(new Error('private provider response'), { status: 429 }); } });
  assert.ok(calls <= 2);
  assert.equal(result.status, 'blocked');
  assert.ok(!JSON.stringify(result).includes('private provider response'));
});
