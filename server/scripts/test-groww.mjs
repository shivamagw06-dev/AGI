#!/usr/bin/env node
/**
 * Test Groww API connectivity — run from server folder:
 *   node scripts/test-groww.mjs
 *
 * Loads server/.env — never prints secrets or full tokens.
 */

import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '../.env') });

const {
  isGrowwConfigured,
  getQuote,
  getLTP,
  getOHLC,
} = await import('../providers/groww.js');

function mask(obj) {
  if (obj == null) return obj;
  if (typeof obj === 'number') return obj;
  if (typeof obj === 'object' && !Array.isArray(obj)) {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (/price|ltp|last|open|high|low|close|change/i.test(k)) {
        out[k] = typeof v === 'number' ? v : '[present]';
      } else if (k === 'ohlc' && typeof v === 'object') {
        out[k] = { open: v.open, close: v.close };
      } else {
        out[k] = typeof v === 'object' ? '[object]' : v;
      }
    }
    return out;
  }
  return obj;
}

async function runTest(name, fn) {
  try {
    const result = await fn();
    console.log(`✅ ${name}`);
    console.log(JSON.stringify(mask(result), null, 2));
    return { ok: true, name };
  } catch (err) {
    console.log(`❌ ${name}: ${err.message}`);
    return { ok: false, name, error: err.message };
  }
}

console.log('=== Groww API Health Check ===\n');
const accessToken = (process.env.GROWW_ACCESS_TOKEN || '').trim();
const apiKey = (process.env.GROWW_API_KEY || '').trim();
const apiSecret = (process.env.GROWW_API_SECRET || '').trim();
const authMode = accessToken
  ? 'ACCESS_TOKEN'
  : apiKey.startsWith('eyJ') && apiKey.length > 100
    ? 'API_KEY (JWT — will use as access token)'
    : 'API_KEY+SECRET';

console.log('Configured:', isGrowwConfigured());
console.log('Auth mode:', authMode);
console.log('API secret length:', apiSecret.length, apiSecret.length < 8 ? '(too short — fix .env)' : '');
console.log('');

if (!isGrowwConfigured()) {
  console.error('Set GROWW_ACCESS_TOKEN or GROWW_API_KEY + GROWW_API_SECRET in server/.env');
  process.exit(1);
}

const results = [];

results.push(
  await runTest('Get Quote — NIFTY (exchange=NSE, segment=CASH, trading_symbol=NIFTY)', () =>
    getQuote('NSE', 'CASH', 'NIFTY')
  )
);

results.push(
  await runTest('Get LTP — NSE_NIFTY, NSE_RELIANCE (segment=CASH, exchange_symbols=...)', () =>
    getLTP(['NSE_NIFTY', 'NSE_RELIANCE'])
  )
);

results.push(
  await runTest('Get OHLC — NSE_NIFTY (segment=CASH, exchange_symbols=...)', () =>
    getOHLC(['NSE_NIFTY'])
  )
);

results.push(
  await runTest('Get Quote — RELIANCE', () => getQuote('NSE', 'CASH', 'RELIANCE'))
);

const passed = results.filter((r) => r.ok).length;
console.log(`\n=== ${passed}/${results.length} tests passed ===`);

process.exit(passed === results.length ? 0 : 1);
