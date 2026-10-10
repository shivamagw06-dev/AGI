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

test('one blocked index does not stop other instruments and retries retain progress', async () => {
  const recoveredKeys = new Set(), calls = [];
  const candles = [['2026-10-05T06:00:00Z',100,101,99,100,10]];
  const args = {instrumentKeys:['INDEX','A','B','C'], featureStore:new IntradayFeatureStore(), recoveredKeys, delayMs:0, now:()=>new Date('2026-10-05T07:00:00Z'),
    fetchCandles:async key=>{calls.push(key);if(key==='INDEX')throw Object.assign(new Error('private response'),{status:429,localBudget:true});return {data:{candles}};}};
  const first=await bootstrapLiveAlphaIntraday(args);
  assert.equal(first.status,'partial');assert.equal(first.restored,3);assert.equal(first.failures[0].reason,'local_budget_deferred');
  assert.ok(!JSON.stringify(first).includes('private response'));
  calls.length=0;
  const second=await bootstrapLiveAlphaIntraday({...args,fetchCandles:async key=>{calls.push(key);return {data:{candles}};}});
  assert.deepEqual(calls,['INDEX']);assert.equal(second.restored,4);assert.equal(second.status,'ready');
});

test('a previous session or unfinished candle is not counted as restored', async () => {
  const result = await bootstrapLiveAlphaIntraday({ instrumentKeys: ['A'], featureStore: new IntradayFeatureStore(), delayMs: 0, now: () => new Date('2026-10-05T07:00:00Z'), fetchCandles: async () => ({data:{candles:[['2026-10-04T06:00:00Z',100,101,99,100],['2026-10-05T07:00:00Z',100,101,99,100]]}}) });
  assert.equal(result.restored, 0);
  assert.equal(result.failed, 1);
  assert.equal(result.status, 'partial');
});
