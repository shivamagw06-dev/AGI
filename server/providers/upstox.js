/**
 * Upstox Developer API — fundamentals / corporate actions.
 * Docs: https://upstox.com/developer/api-documentation/get-corporate-actions/
 *
 * Auth: Bearer access token from the Upstox developer dashboard (or OAuth).
 * Accepts common env aliases because operators often paste into UPSTOX_API.
 */

const UPSTOX_BASE = process.env.UPSTOX_API_BASE || 'https://api.upstox.com/v2';

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

function firstEnv(...keys) {
  for (const key of keys) {
    const value = String(process.env[key] || '').trim();
    if (value) return { key, value };
  }
  return { key: null, value: '' };
}

/** Access token used as Authorization: Bearer … */
export function resolveUpstoxAccessToken() {
  // Prefer explicit access-token names, then common misnames (UPSTOX_API).
  const hit = firstEnv(
    'UPSTOX_ACCESS_TOKEN',
    'UPSTOX_TOKEN',
    'UPSTOX_API',
    'UPSTOX_API_TOKEN',
    'UPSTOX_API_KEY' // only if someone pasted the daily token into API_KEY
  );
  if (!hit.value) return { token: '', source: null };

  // If UPSTOX_API / UPSTOX_API_KEY looks like a short client_id (not a token),
  // do not treat it as a Bearer token — corporate-actions needs the access token.
  if (
    (hit.key === 'UPSTOX_API' || hit.key === 'UPSTOX_API_KEY') &&
    hit.value.length < 40 &&
    !hit.value.includes('.')
  ) {
    return { token: '', source: hit.key, likely_client_id: true };
  }

  return { token: hit.value, source: hit.key, likely_client_id: false };
}

export function upstoxEnvPresence() {
  const keys = [
    'UPSTOX_ACCESS_TOKEN',
    'UPSTOX_TOKEN',
    'UPSTOX_API',
    'UPSTOX_API_TOKEN',
    'UPSTOX_API_KEY',
    'UPSTOX_API_SECRET',
    'UPSTOX_CLIENT_ID',
    'UPSTOX_CLIENT_SECRET',
    'UPSTOX_REDIRECT_URI',
  ];
  const present = {};
  for (const key of keys) {
    present[key] = Boolean(String(process.env[key] || '').trim());
  }
  return present;
}

export function isUpstoxConfigured() {
  const { token } = resolveUpstoxAccessToken();
  return Boolean(token);
}

async function upstoxGet(path) {
  const { token, source, likely_client_id } = resolveUpstoxAccessToken();
  if (!token) {
    if (likely_client_id) {
      throw new Error(
        `Upstox env ${source} looks like a client_id/API key, not an access token. ` +
          'Set UPSTOX_ACCESS_TOKEN to the Bearer token from the Upstox developer app (Generate token).'
      );
    }
    throw new Error(
      'Upstox auth missing: set UPSTOX_ACCESS_TOKEN (Bearer token). ' +
        'API key/secret alone cannot call corporate-actions.'
    );
  }

  const fetchFn = await ensureFetch();
  const url = `${UPSTOX_BASE}${path}`;
  const resp = await fetchFn(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const msg =
      json?.errors?.[0]?.message ||
      json?.message ||
      json?.error ||
      `Upstox HTTP ${resp.status}`;
    const err = new Error(String(msg));
    err.status = resp.status;
    err.body = json;
    throw err;
  }
  return json;
}

function cleanIsin(isin) {
  const clean = String(isin || '').trim().toUpperCase();
  if (!/^INE[A-Z0-9]{9}$/.test(clean) && !/^[A-Z]{2}[A-Z0-9]{9,12}$/.test(clean)) {
    throw new Error(`Invalid ISIN: ${isin}`);
  }
  return clean;
}

/**
 * ISIN-keyed fundamentals endpoints, as published by the Upstox Python SDK
 * (`/v2/fundamentals/{isin}/...`). Note the profile path is `profile`, not
 * `company-profile`. `competitors` is keyed by instrument_key instead.
 */
export const FUNDAMENTAL_ENDPOINTS = Object.freeze([
  'profile',
  'income-statement',
  'balance-sheet',
  'cash-flow',
  'key-ratios',
  'share-holdings',
  'corporate-actions',
]);

/**
 * GET /fundamentals/{isin}/{endpoint}
 * @param {string} isin e.g. INE002A01018 (Reliance)
 * @param {string} endpoint one of FUNDAMENTAL_ENDPOINTS
 * @param {{ type?: string, time_period?: string, fs?: boolean }} [query]
 */
export async function getFundamentals(isin, endpoint, query = {}) {
  if (!FUNDAMENTAL_ENDPOINTS.includes(endpoint)) {
    throw new Error(`Unsupported fundamentals endpoint: ${endpoint}`);
  }
  const params = new URLSearchParams();
  const type = query.type || 'consolidated';
  const timePeriod = query.time_period || query.timePeriod;
  if (type) params.set('type', type);
  if (timePeriod) params.set('time_period', timePeriod);
  if (query.fs !== false && ['income-statement', 'balance-sheet', 'cash-flow'].includes(endpoint)) {
    params.set('fs', 'true');
  }
  const qs = params.toString();
  const path = `/fundamentals/${encodeURIComponent(cleanIsin(isin))}/${endpoint}${qs ? `?${qs}` : ''}`;
  return upstoxGet(path);
}

export async function getCorporateActions(isin) {
  return getFundamentals(isin, 'corporate-actions');
}

/** Canonical exchange calendar inputs used by AGI schedulers and horizons. */
export async function getMarketHolidays(date = null) {
  const suffix = date ? `/${encodeURIComponent(String(date))}` : '';
  return upstoxGet(`/market/holidays${suffix}`);
}

export async function getMarketTimings(date) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(date || ''))) {
    throw new Error('Upstox market timings require date in YYYY-MM-DD format.');
  }
  return upstoxGet(`/market/timings/${encodeURIComponent(String(date))}`);
}

export async function getExchangeStatus(exchange = 'NSE') {
  const value = String(exchange || '').trim().toUpperCase();
  if (!/^[A-Z0-9_-]{2,12}$/.test(value)) throw new Error('Invalid exchange.');
  return upstoxGet(`/market/status/${encodeURIComponent(value)}`);
}

/** GET /v2/fundamentals/{instrument_key}/competitors — keyed by instrument_key, not ISIN. */
export async function getCompetitors(instrumentKey) {
  const key = String(instrumentKey || '').trim();
  if (!key.includes('|')) throw new Error(`Invalid instrument_key: ${instrumentKey}`);
  return upstoxGet(`/fundamentals/${encodeURIComponent(key)}/competitors`);
}

/**
 * Historical OHLC candles. Public data — works without an access token.
 * @param {string} instrumentKey e.g. "NSE_EQ|INE002A01018"
 * @param {string} unit days | weeks | months | minutes | hours
 */
export async function getHistoricalCandles(instrumentKey, { unit = 'months', interval = 1, from, to } = {}) {
  const key = String(instrumentKey || '').trim();
  if (!key.includes('|')) throw new Error(`Invalid instrument_key: ${instrumentKey}`);
  if (!to) throw new Error('Upstox historical candles require a to date');
  const base = process.env.UPSTOX_API_BASE_V3 || 'https://api.upstox.com/v3';
  const path = `/historical-candle/${encodeURIComponent(key)}/${unit}/${interval}/${to}${from ? `/${from}` : ''}`;
  const fetchFn = await ensureFetch();
  const { token } = resolveUpstoxAccessToken();
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetchFn(`${base}${path}`, { headers });
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(json?.errors?.[0]?.message || `Upstox HTTP ${resp.status}`);
    err.status = resp.status;
    throw err;
  }
  return json;
}

/** Current-session OHLCV; kept separate from end-of-day factor history. */
export async function getIntradayCandles(instrumentKey, { unit = 'minutes', interval = 15 } = {}) {
  const key = String(instrumentKey || '').trim();
  if (!key.includes('|')) throw new Error(`Invalid instrument_key: ${instrumentKey}`);
  const { token } = resolveUpstoxAccessToken();
  if (!token) throw new Error('Upstox auth missing: set UPSTOX_ACCESS_TOKEN for intraday candles.');
  const base = process.env.UPSTOX_API_BASE_V3 || 'https://api.upstox.com/v3';
  const path = `/historical-candle/intraday/${encodeURIComponent(key)}/${unit}/${interval}`;
  const fetchFn = await ensureFetch();
  const resp = await fetchFn(`${base}${path}`, {
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
  });
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(json?.errors?.[0]?.message || `Upstox HTTP ${resp.status}`);
    err.status = resp.status;
    throw err;
  }
  return json;
}

/**
 * Exchange-level FII/DII — GET /v2/market/fii and /v2/market/dii
 * Upstox currently accepts: NSE_EQ|CASH, NSE_FO|INDEX_FUTURES, ...
 * @param {{ dataType?: string, interval?: '1D'|'1M' }} opts
 */
export const FII_DATA_TYPES = Object.freeze(['NSE_EQ|CASH', 'NSE_FO|INDEX_FUTURES', 'NSE_FO|STOCK_FUTURES', 'NSE_FO|INDEX_OPTIONS', 'NSE_FO|STOCK_OPTIONS']);
function activityQuery(dataTypes, interval, from) { const params = new URLSearchParams(); for (const value of dataTypes) params.append('data_type', value); params.set('interval', interval); if (from) params.set('from', from); return params.toString(); }
function istDateFromTimestamp(value) { const timestamp = Number(value); if (!Number.isFinite(timestamp)) return null; const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(timestamp)); const get = (type) => parts.find((part) => part.type === type)?.value; return `${get('year')}-${get('month')}-${get('day')}`; }
export function normalizeInstitutionalActivity(payload, participant, interval = '1D') {
  const output = [];
  for (const [segment, values] of Object.entries(payload?.data ?? payload ?? {})) for (const row of (Array.isArray(values) ? values : [values].filter(Boolean))) {
    const timestamp = Number(row?.time_stamp ?? row?.timestamp);
    output.push({ participant, segment, interval, observation_date: istDateFromTimestamp(timestamp), time_stamp: Number.isFinite(timestamp) ? timestamp : null, buy_amount: row?.buy_amount ?? null, sell_amount: row?.sell_amount ?? null, buy_contracts: row?.buy_contracts ?? null, sell_contracts: row?.sell_contracts ?? null, oi_contracts: row?.oi_contracts ?? null, oi_amount: row?.oi_amount ?? null, long_contracts: row?.total_long_contracts ?? null, short_contracts: row?.total_short_contracts ?? null, call_long_contracts: row?.total_call_long_contracts ?? null, put_long_contracts: row?.total_put_long_contracts ?? null, call_short_contracts: row?.total_call_short_contracts ?? null, put_short_contracts: row?.total_put_short_contracts ?? null, source: 'upstox' });
  }
  return output.filter((row) => row.observation_date);
}
export async function getMarketFii({ dataTypes = FII_DATA_TYPES, interval = '1D', from } = {}) { const requested = [...new Set((dataTypes || []).filter((value) => FII_DATA_TYPES.includes(value)))]; if (!requested.length) throw new Error('At least one valid FII data type is required.'); return upstoxGet(`/market/fii?${activityQuery(requested, interval, from)}`); }
export async function getMarketDii({ interval = '1D', from } = {}) { return upstoxGet(`/market/dii?${activityQuery(['NSE_EQ|CASH'], interval, from)}`); }
export async function getMarketFiiDii({ dataTypes, dataType, interval = '1D', from } = {}) { const requested = dataTypes || (dataType ? [dataType] : FII_DATA_TYPES); const [fii, dii] = await Promise.all([getMarketFii({ dataTypes: requested, interval, from }), getMarketDii({ interval, from })]); return { ok: true, interval, from: from || null, data_types: requested, observations: [...normalizeInstitutionalActivity(fii, 'FII', interval), ...normalizeInstitutionalActivity(dii, 'DII', interval)] }; }
