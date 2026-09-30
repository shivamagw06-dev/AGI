import test from 'node:test';
import assert from 'node:assert/strict';
import { clearNseScreenerCache, getNseScreenerUniverse, normalizeQuote } from './nseScreenerService.js';

test('quote normalization computes change against the previous close', () => {
  assert.deepEqual(normalizeQuote({ last_price: 105, prev_close_price: 100, volume: 1500, year_high: 120, year_low: 80, timestamp: '2026-09-30T10:00:00+05:30' }), {
    lastPrice: 105,
    previousClose: 100,
    changePercent: 5,
    volume: 1500,
    yearHigh: 120,
    yearLow: 80,
    quoteTime: '2026-09-30T10:00:00+05:30',
  });
  assert.equal(normalizeQuote({ last_price: 100, prev_close_price: 0 }).changePercent, null);
});

test('NSE screen merges quotes without inventing AGI research for uncovered equities', async () => {
  const originalFetch = globalThis.fetch;
  const originalToken = process.env.UPSTOX_ACCESS_TOKEN;
  const originalUrl = process.env.SUPABASE_URL;
  const originalKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  delete process.env.SUPABASE_URL;
  delete process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.UPSTOX_ACCESS_TOKEN = 'test-token-for-market-data-only';
  globalThis.fetch = async (url) => {
    if (String(url).includes('NSE.json.gz')) {
      const instruments = [
        { segment: 'NSE_EQ', instrument_type: 'EQ', trading_symbol: 'AAA', name: 'AAA LTD', isin: 'INE123A01010', instrument_key: 'NSE_EQ|INE123A01010' },
        { segment: 'NSE_EQ', instrument_type: 'EQ', trading_symbol: 'BBB', name: 'BBB LTD', isin: 'INE456A01010', instrument_key: 'NSE_EQ|INE456A01010' },
        { segment: 'NSE_FO', instrument_type: 'FUT', trading_symbol: 'AAA', name: 'AAA FUT', isin: 'INE123A01010' },
      ];
      return { ok: true, arrayBuffer: async () => Buffer.from(JSON.stringify(instruments)) };
    }
    if (String(url).includes('/market-quote/quotes')) {
      return { ok: true, json: async () => ({ status: 'success', data: { 'NSE_EQ:AAA': { last_price: 105, prev_close_price: 100, volume: 1200 } } }) };
    }
    throw new Error(`Unexpected URL: ${url}`);
  };
  clearNseScreenerCache();
  try {
    const result = await getNseScreenerUniverse();
    assert.equal(result.items.length, 2);
    assert.equal(result.quoteCount, 1);
    assert.equal(result.items[0].changePercent, 5);
    assert.equal(result.items[0].hasResearch, false);
    assert.equal(result.items[0].agiResearchScore, undefined);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalToken === undefined) delete process.env.UPSTOX_ACCESS_TOKEN; else process.env.UPSTOX_ACCESS_TOKEN = originalToken;
    if (originalUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = originalUrl;
    if (originalKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = originalKey;
    clearNseScreenerCache();
  }
});
