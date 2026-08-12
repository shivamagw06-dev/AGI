/**
 * Groww Trading API provider — primary market data source.
 * Docs: https://groww.in/trade-api/docs/curl
 *
 * Auth: set GROWW_ACCESS_TOKEN (daily token from Groww dashboard)
 *   or GROWW_API_KEY + GROWW_API_SECRET for checksum flow.
 */

import crypto from 'crypto';

const GROWW_BASE = process.env.GROWW_API_BASE || 'https://api.groww.in/v1';

let cachedToken = null;
let tokenExpiry = 0;

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

function generateChecksum(secret, timestamp) {
  return crypto.createHash('sha256').update(secret + timestamp).digest('hex');
}

function looksLikeAccessToken(value) {
  // Daily access tokens from Groww dashboard are JWTs; API keys are short opaque strings.
  return value.startsWith('eyJ') && value.length > 100;
}

export async function resolveGrowwAccessToken() {
  const direct = (process.env.GROWW_ACCESS_TOKEN || '').trim();
  if (direct) return direct;

  const apiKey = (process.env.GROWW_API_KEY || '').trim();
  const apiSecret = (process.env.GROWW_API_SECRET || '').trim();

  // Common setup mistake: access token pasted into GROWW_API_KEY.
  if (!direct && looksLikeAccessToken(apiKey)) return apiKey;

  if (cachedToken && Date.now() < tokenExpiry) return cachedToken;

  if (!apiKey || !apiSecret) {
    throw new Error(
      'Groww auth missing: set GROWW_ACCESS_TOKEN or GROWW_API_KEY + GROWW_API_SECRET in server/.env'
    );
  }

  if (apiSecret.length < 8) {
    throw new Error(
      'Groww API secret looks invalid (too short). Copy the full secret from Groww Cloud API Keys, or use GROWW_ACCESS_TOKEN from Trading APIs.'
    );
  }

  const timestamp = Math.floor(Date.now() / 1000).toString();
  const checksum = generateChecksum(apiSecret, timestamp);
  const fetchFn = await ensureFetch();

  const resp = await fetchFn(`${GROWW_BASE}/token/api/access`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ key_type: 'approval', checksum, timestamp }),
  });

  const json = await resp.json().catch(() => ({}));
  if (json?.token) {
    cachedToken = json.token;
    tokenExpiry = Date.now() + 23 * 60 * 60 * 1000;
    return cachedToken;
  }

  const authMsg =
    json?.error?.errorMessage ||
    json?.error?.message ||
    (resp.status === 400 ? 'Invalid credentials — approve the key on Groww Cloud API Keys page' : null);
  throw new Error(authMsg || `Groww token request failed (HTTP ${resp.status})`);
}

export function isGrowwConfigured() {
  return Boolean(
    (process.env.GROWW_ACCESS_TOKEN || '').trim() ||
      ((process.env.GROWW_API_KEY || '').trim() && (process.env.GROWW_API_SECRET || '').trim())
  );
}

async function growwRequest(path, params = {}) {
  const token = await resolveGrowwAccessToken();

  const url = new URL(`${GROWW_BASE}${path}`);
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '') url.searchParams.set(k, String(v));
  });

  const fetchFn = await ensureFetch();
  const resp = await fetchFn(url.toString(), {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      'X-API-VERSION': '1.0',
    },
  });

  const json = await resp.json().catch(() => ({}));
  if (json?.status === 'SUCCESS') return json.payload;
  const msg = json?.error?.message || json?.error?.errorMessage || `Groww request failed (${resp.status})`;
  if (resp.status === 429 || /rate limit/i.test(msg)) {
    const err = new Error('Groww rate limit exceeded');
    err.isRateLimit = true;
    throw err;
  }
  throw new Error(msg);
}

/** Batch LTP — up to 50 symbols per call */
export async function getLTP(exchangeSymbols, segment = 'CASH') {
  if (!exchangeSymbols?.length) return {};
  const payload = await growwRequest('/live-data/ltp', {
    segment,
    exchange_symbols: exchangeSymbols.join(','),
  });
  return payload || {};
}

/** Full quote for a single instrument */
export async function getQuote(exchange, segment, tradingSymbol) {
  return growwRequest('/live-data/quote', {
    exchange,
    segment,
    trading_symbol: tradingSymbol,
  });
}

/** Batch OHLC */
export async function getOHLC(exchangeSymbols, segment = 'CASH') {
  if (!exchangeSymbols?.length) return {};
  return growwRequest('/live-data/ohlc', {
    segment,
    exchange_symbols: exchangeSymbols.join(','),
  });
}

const formatGrowwDate = (date) => date.toISOString().slice(0, 19).replace('T', ' ');

/** Historical daily candle range — backend only; callers must not expose raw candles publicly. */
export async function getHistoricalCandleRange(
  exchange,
  segment,
  tradingSymbol,
  start,
  end,
  intervalMinutes = 1440
) {
  const payload = await growwRequest('/historical/candle/range', {
    exchange,
    segment,
    trading_symbol: tradingSymbol,
    start_time: formatGrowwDate(start),
    end_time: formatGrowwDate(end),
    interval_in_minutes: String(intervalMinutes),
  });
  return payload?.candles || [];
}

/** Historical daily candles for indicator calculation — backend only */
export async function getHistoricalCandles(exchange, segment, tradingSymbol, days = 120) {
  const end = new Date();
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
  try {
    return await getHistoricalCandleRange(exchange, segment, tradingSymbol, start, end);
  } catch {
    return [];
  }
}

export const INDEX_SYMBOLS = [
  { key: 'nifty', exchange: 'NSE', symbol: 'NIFTY', label: 'Nifty 50' },
  { key: 'banknifty', exchange: 'NSE', symbol: 'BANKNIFTY', label: 'Bank Nifty' },
  { key: 'vix', exchange: 'NSE', symbol: 'INDIA VIX', label: 'India VIX' },
];

/** Universe for the AGI index-sentiment model. No raw market fields leave the service. */
export const INDEX_SENTIMENT_UNIVERSE = [
  { key: 'nifty50', exchange: 'NSE', symbol: 'NIFTY', label: 'Nifty 50' },
  { key: 'banknifty', exchange: 'NSE', symbol: 'BANKNIFTY', label: 'Bank Nifty' },
  { key: 'finnifty', exchange: 'NSE', symbol: 'FINNIFTY', label: 'Fin Nifty' },
  { key: 'midcap', exchange: 'NSE', symbol: 'MIDCPNIFTY', label: 'Nifty Midcap' },
  { key: 'next50', exchange: 'NSE', symbol: 'NIFTYNXT50', label: 'Nifty Next 50' },
  { key: 'nifty100', exchange: 'NSE', symbol: 'NIFTY100', label: 'Nifty 100' },
  { key: 'nifty200', exchange: 'NSE', symbol: 'NIFTY200', label: 'Nifty 200' },
  { key: 'nifty500', exchange: 'NSE', symbol: 'NIFTY500', label: 'Nifty 500' },
  { key: 'midcap100', exchange: 'NSE', symbol: 'NIFTYMIDCAP100', label: 'Nifty Midcap 100' },
  { key: 'smallcap100', exchange: 'NSE', symbol: 'NIFTYSMALLCAP100', label: 'Nifty Smallcap 100' },
  { key: 'niftyit', exchange: 'NSE', symbol: 'NIFTYIT', label: 'Nifty IT' },
  { key: 'niftyauto', exchange: 'NSE', symbol: 'NIFTYAUTO', label: 'Nifty Auto' },
  { key: 'niftypharma', exchange: 'NSE', symbol: 'NIFTYPHARMA', label: 'Nifty Pharma' },
  { key: 'niftypsubank', exchange: 'NSE', symbol: 'NIFTYPSUBANK', label: 'Nifty PSU Bank' },
  { key: 'niftyrealty', exchange: 'NSE', symbol: 'NIFTYREALTY', label: 'Nifty Realty' },
  { key: 'niftyfmcg', exchange: 'NSE', symbol: 'NIFTYFMCG', label: 'Nifty FMCG' },
  { key: 'niftymetal', exchange: 'NSE', symbol: 'NIFTYMETAL', label: 'Nifty Metal' },
  { key: 'sensex', exchange: 'BSE', symbol: 'SENSEX', label: 'Sensex' },
  { key: 'bankex', exchange: 'BSE', symbol: 'BANKEX', label: 'BSE Bankex' },
];

export const TRACKED_STOCKS = [
  { symbol: 'RELIANCE', label: 'Reliance' },
  { symbol: 'TCS', label: 'TCS' },
  { symbol: 'HDFCBANK', label: 'HDFC Bank' },
  { symbol: 'INFY', label: 'Infosys' },
  { symbol: 'BEL', label: 'BEL' },
  { symbol: 'HAL', label: 'HAL' },
];

const DEFAULT_SECTORS = [
  { name: 'Capital Goods', change: 2.8 },
  { name: 'Defence', change: 2.4 },
  { name: 'Power', change: 2.2 },
  { name: 'Banks', change: 1.4 },
  { name: 'Pharma', change: 0.6 },
  { name: 'Auto', change: 0.3 },
  { name: 'IT', change: -0.8 },
  { name: 'FMCG', change: -1.2 },
];

export const TICKER_INSTRUMENTS = [
  { id: 'nifty50', label: 'NIFTY 50', exchange: 'NSE', symbol: 'NIFTY', growwKey: 'NSE_NIFTY' },
  { id: 'banknifty', label: 'BANK NIFTY', exchange: 'NSE', symbol: 'BANKNIFTY', growwKey: 'NSE_BANKNIFTY' },
  { id: 'sensex', label: 'SENSEX', exchange: 'BSE', symbol: 'SENSEX', growwKey: 'BSE_SENSEX' },
  { id: 'vix', label: 'INDIA VIX', exchange: 'NSE', symbol: 'INDIA VIX', growwKey: 'NSE_INDIA VIX' },
];

function parseOhlc(raw) {
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw.replace(/(\w+):/g, '"$1":'));
    } catch {
      return null;
    }
  }
  return null;
}

function pctChange(ltp, close) {
  const last = Number(ltp);
  const prev = Number(close);
  if (!Number.isFinite(last) || !Number.isFinite(prev) || prev === 0) return null;
  return ((last - prev) / prev) * 100;
}

/** Fetch normalized ticker — 2 batch Groww calls (LTP + OHLC) to stay within rate limits */
export async function fetchGrowwTicker() {
  const instruments = TICKER_INSTRUMENTS;
  const keys = instruments.map((i) => i.growwKey);

  const [ltpMap, ohlcMap] = await Promise.all([
    getLTP(keys).catch(() => ({})),
    getOHLC(keys).catch(() => ({})),
  ]);

  return instruments.map((inst) => {
    const ltp = ltpMap[inst.growwKey];
    const ohlc = parseOhlc(ohlcMap[inst.growwKey]);
    const price = ltp ?? ohlc?.close ?? null;
    const close = ohlc?.close ?? ohlc?.open ?? null;
    const percentChange = pctChange(price, close);
    const change =
      price != null && close != null && Number.isFinite(Number(price)) && Number.isFinite(Number(close))
        ? Number(price) - Number(close)
        : null;

    return {
      id: inst.id,
      name: inst.label,
      price,
      change,
      percentChange,
      source: 'groww',
    };
  });
}
