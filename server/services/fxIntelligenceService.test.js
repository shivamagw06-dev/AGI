import assert from 'node:assert/strict';
import test from 'node:test';
import {
  fetchUpstoxGlobalFxQuotes,
  normalizeUpstoxGlobalCandle,
  normalizeUpstoxGlobalLtp,
  UPSTOX_GLOBAL_TARGETS,
} from '../providers/upstoxFx.js';
import { fetchFxIntelligence, mergeFxProviders } from './fxIntelligenceService.js';

const yahooPayload = {
  ok: true,
  pairs: [{
    pair: 'USD/INR', base: 'USD', quote: 'INR', price: 100, low: 98, high: 102,
    returns: { d1: 1, w1: 2, m1: 4 }, sparkline: [98, 99, 100], source: 'Yahoo Finance',
  }],
  drivers: [{
    name: 'Brent crude', price: 90, low: 88, high: 92,
    returns: { d1: -1, w1: 3, m1: 5 }, sparkline: [88, 91, 90], source: 'Yahoo Finance',
  }],
  strength: { d1: [], w1: [], m1: [] },
  asOf: '2026-08-24T10:00:00.000Z',
};

test('normalizes the official Upstox LTP V3 response by instrument token', () => {
  const quotes = normalizeUpstoxGlobalLtp({
    status: 'success',
    data: {
      'GLOBAL_INDICATOR:USDINR': {
        last_price: 101.25,
        instrument_token: 'GLOBAL_INDICATOR|USDINR',
        volume: 0,
        cp: 100,
      },
      'GLOBAL_INDICATOR:BZUSD': {
        last_price: 91.5,
        instrument_token: 'GLOBAL_INDICATOR|BZUSD',
        volume: 0,
        cp: 90,
      },
    },
  }, { fetchedAt: '2026-08-24T10:05:00.000Z' });

  assert.equal(quotes.length, 2);
  assert.equal(quotes[0].target, 'USD/INR');
  assert.equal(quotes[0].price, 101.25);
  assert.equal(quotes[0].previousClose, 100);
  assert.equal(quotes[0].latencySeconds, 20);
});

test('normalizes the latest official Upstox intraday candle without inventing a previous close', () => {
  const quote = normalizeUpstoxGlobalCandle(UPSTOX_GLOBAL_TARGETS[1], {
    status: 'success',
    data: { candles: [['2026-08-25T02:13:00+05:30', 90.31, 90.31, 90.31, 90.31, 0, 0]] },
  });

  assert.equal(quote.target, 'Brent crude');
  assert.equal(quote.price, 90.31);
  assert.equal(quote.previousClose, null);
  assert.equal(quote.latencySeconds, 60);
  assert.equal(quote.quoteMode, '1-minute candle');
});

test('falls back per instrument to Upstox intraday candles when global LTP rejects published keys', async () => {
  const fetchFn = async (url) => {
    if (url.includes('/market-quote/ltp')) {
      return {
        ok: false,
        status: 400,
        json: async () => ({ errors: [{ errorCode: 'UDAPI100095', message: 'Invalid Instrument key' }] }),
      };
    }
    const isBrent = url.includes('BZUSD');
    return {
      ok: true,
      status: 200,
      json: async () => ({
        status: 'success',
        data: { candles: isBrent ? [['2026-08-25T02:13:00+05:30', 90, 91, 89, 90.31, 0, 0]] : [] },
      }),
    };
  };

  const result = await fetchUpstoxGlobalFxQuotes({ fetchFn, token: 'test-token' });

  assert.equal(result.ok, true);
  assert.equal(result.mode, 'intraday_fallback');
  assert.equal(result.reason, 'partial_intraday_fallback');
  assert.equal(result.quotes.length, 1);
  assert.equal(result.quotes[0].target, 'Brent crude');
});

test('overlays latest Upstox prices while preserving Yahoo historical anchors', () => {
  const merged = mergeFxProviders(yahooPayload, {
    ok: true,
    configured: true,
    latencySeconds: 20,
    quotes: [{
      target: 'USD/INR', kind: 'pair', price: 101, previousClose: 100,
      source: 'Upstox Global Indicator', latencySeconds: 20,
      instrumentKey: 'GLOBAL_INDICATOR|USDINR', fetchedAt: '2026-08-24T10:05:00.000Z',
    }],
  });

  assert.equal(merged.pairs[0].price, 101);
  assert.equal(merged.pairs[0].returns.d1, 1);
  assert.equal(merged.pairs[0].sparkline.at(-1), 101);
  assert.equal(merged.pairs[0].historySource, 'Yahoo Finance');
  assert.equal(merged.pairs[0].source, 'Upstox Global Indicator');
  assert.equal(merged.providers.upstox.ok, true);
  assert.equal(merged.providers.upstox.targets, 2);
  assert.match(merged.source, /Upstox/);
});

test('fails open to the complete Yahoo payload when Upstox is unavailable', async () => {
  const result = await fetchFxIntelligence({
    yahooFetcher: async () => yahooPayload,
    upstoxFetcher: async () => { const error = new Error('expired'); error.status = 401; throw error; },
  });

  assert.equal(result.pairs[0].price, 100);
  assert.equal(result.providers.upstox.ok, false);
  assert.equal(result.providers.upstox.reason, 'authentication_failed');
  assert.match(result.source, /fallback/);
});
