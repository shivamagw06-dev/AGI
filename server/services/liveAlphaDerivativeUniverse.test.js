import assert from 'node:assert/strict';
import test from 'node:test';
import { resolveLiveAlphaDerivatives } from './liveAlphaDerivativeUniverse.js';

test('resolves current-month futures by exact underlying key', async () => {
  const priorToken = process.env.UPSTOX_ACCESS_TOKEN;
  process.env.UPSTOX_ACCESS_TOKEN = 'test-access-token-with-enough-length-abcdefgh';
  const universe = {
    benchmarkKey: 'NSE_INDEX|Nifty 50',
    members: Array.from({ length: 10 }, (_, index) => ({ symbol: `S${index}`, instrumentKey: `NSE_EQ|ISIN${index}` })),
  };
  const calls = [];
  const result = await resolveLiveAlphaDerivatives(universe, { fetchFn: async (url) => {
    calls.push(url);
    const symbol = new URL(url).searchParams.get('query');
    const index = Number(symbol.slice(1));
    return { ok: true, json: async () => ({ data: [
      { segment: 'NSE_FO', instrument_type: 'FUT', underlying_key: `NSE_EQ|OTHER${index}`, instrument_key: `NSE_FO|WRONG${index}`, expiry: '2026-08-27' },
      { segment: 'NSE_FO', instrument_type: 'FUT', underlying_key: `NSE_EQ|ISIN${index}`, instrument_key: `NSE_FO|RIGHT${index}`, expiry: '2026-08-27' },
    ] }) };
  } });
  assert.equal(calls.length, 10);
  assert.equal(result.derivativeResolution.status, 'ready');
  assert.equal(result.derivativeResolution.resolved, 10);
  assert.equal(result.members[0].derivativeInstrumentKey, 'NSE_FO|RIGHT0');
  if (priorToken === undefined) delete process.env.UPSTOX_ACCESS_TOKEN;
  else process.env.UPSTOX_ACCESS_TOKEN = priorToken;
});

test('keeps runtime usable when derivative discovery is unavailable', async () => {
  const priorToken = process.env.UPSTOX_ACCESS_TOKEN;
  delete process.env.UPSTOX_ACCESS_TOKEN;
  const universe = { benchmarkKey: 'NSE_INDEX|Nifty 50', members: [{ symbol: 'S0', instrumentKey: 'NSE_EQ|ISIN0' }] };
  const result = await resolveLiveAlphaDerivatives(universe, { fetchFn: async () => { throw new Error('must not run'); } });
  assert.equal(result.derivativeResolution.status, 'unavailable');
  assert.equal(result.members[0].derivativeInstrumentKey, undefined);
  if (priorToken !== undefined) process.env.UPSTOX_ACCESS_TOKEN = priorToken;
});
