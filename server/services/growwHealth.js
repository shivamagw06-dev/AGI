/**
 * Groww API health check — backend diagnostic (no secrets in response).
 * Compares our REST usage with official docs:
 *   Quote: GET /live-data/quote?exchange&segment&trading_symbol
 *   LTP:   GET /live-data/ltp?segment&exchange_symbols=NSE_NIFTY,...
 *   OHLC:  GET /live-data/ohlc?segment&exchange_symbols=...
 */

import { isGrowwConfigured, getQuote, getLTP, getOHLC } from '../providers/groww.js';

function sanitizeQuote(payload) {
  if (!payload) return null;
  return {
    last_price: payload.last_price ?? null,
    day_change: payload.day_change ?? null,
    day_change_perc: payload.day_change_perc ?? null,
    has_ohlc: Boolean(payload.ohlc),
    volume: payload.volume ?? null,
  };
}

function sanitizeLtp(payload) {
  if (!payload || typeof payload !== 'object') return {};
  const keys = Object.keys(payload);
  return {
    symbols: keys,
    sample: keys[0] ? { [keys[0]]: payload[keys[0]] } : {},
  };
}

function sanitizeOhlc(payload) {
  if (!payload || typeof payload !== 'object') return {};
  const keys = Object.keys(payload);
  const first = keys[0];
  let ohlc = payload[first];
  if (typeof ohlc === 'string') ohlc = { raw: 'string-format' };
  return { symbols: keys, sample: first ? { [first]: ohlc } : {} };
}

export async function getGrowwHealth() {
  const configured = isGrowwConfigured();
  const accessToken = (process.env.GROWW_ACCESS_TOKEN || '').trim();
  const apiKey = (process.env.GROWW_API_KEY || '').trim();
  const apiSecret = (process.env.GROWW_API_SECRET || '').trim();
  const authMode = accessToken
    ? 'access_token'
    : apiKey.startsWith('eyJ') && apiKey.length > 100
      ? 'api_key_jwt_fallback'
      : 'api_key_secret';

  if (!configured) {
    return {
      ok: false,
      configured: false,
      authMode,
      message: 'Set GROWW_ACCESS_TOKEN or GROWW_API_KEY + GROWW_API_SECRET',
      tests: [],
    };
  }

  if (authMode === 'api_key_secret' && apiSecret.length < 8) {
    return {
      ok: false,
      configured: true,
      authMode,
      message: 'GROWW_API_SECRET looks truncated. Copy the full secret from Groww Cloud API Keys.',
      tests: [],
    };
  }

  const tests = [];

  async function test(name, fn) {
    try {
      const data = await fn();
      tests.push({ name, ok: true, data });
    } catch (err) {
      tests.push({ name, ok: false, error: err.message });
    }
  }

  await test('quote:NIFTY', () => getQuote('NSE', 'CASH', 'NIFTY').then(sanitizeQuote));
  await test('ltp:NSE_NIFTY,NSE_RELIANCE', () => getLTP(['NSE_NIFTY', 'NSE_RELIANCE']).then(sanitizeLtp));
  await test('ohlc:NSE_NIFTY', () => getOHLC(['NSE_NIFTY']).then(sanitizeOhlc));

  const passed = tests.filter((t) => t.ok).length;
  return {
    ok: passed === tests.length,
    configured: true,
    authMode,
    passed,
    total: tests.length,
    tests,
    docsNote:
      'REST uses exchange_symbols (cURL). Python SDK uses exchange_trading_symbols — same values like NSE_NIFTY.',
    checkedAt: new Date().toISOString(),
  };
}
