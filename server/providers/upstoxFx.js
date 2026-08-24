import { resolveUpstoxAccessToken } from './upstox.js';

const UPSTOX_V3_BASE = process.env.UPSTOX_API_BASE_V3 || 'https://api.upstox.com/v3';

export const UPSTOX_GLOBAL_TARGETS = Object.freeze([
  {
    id: 'usd-inr',
    target: 'USD/INR',
    kind: 'pair',
    instrumentKey: 'GLOBAL_INDICATOR|USDINR',
    latencySeconds: 20,
  },
  {
    id: 'brent',
    target: 'Brent crude',
    kind: 'driver',
    instrumentKey: 'GLOBAL_INDICATOR|BZUSD',
    latencySeconds: 20,
  },
]);

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

function finitePositive(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

export function normalizeUpstoxGlobalLtp(payload, { fetchedAt = new Date().toISOString() } = {}) {
  const rows = Object.values(payload?.data || {});
  return UPSTOX_GLOBAL_TARGETS.flatMap((target) => {
    const row = rows.find((candidate) => candidate?.instrument_token === target.instrumentKey);
    const price = finitePositive(row?.last_price);
    if (!price) return [];
    return [{
      ...target,
      price,
      previousClose: finitePositive(row?.cp),
      volume: Number.isFinite(Number(row?.volume)) ? Number(row.volume) : null,
      fetchedAt,
      source: 'Upstox Global Indicator',
    }];
  });
}

export async function fetchUpstoxGlobalFxQuotes({ fetchFn, token } = {}) {
  const resolvedToken = token === undefined ? resolveUpstoxAccessToken().token : String(token || '').trim();
  if (!resolvedToken) {
    return { ok: false, configured: false, quotes: [], reason: 'not_configured' };
  }

  const request = fetchFn || await ensureFetch();
  const instrumentKeys = UPSTOX_GLOBAL_TARGETS.map((target) => target.instrumentKey).join(',');
  const url = `${UPSTOX_V3_BASE}/market-quote/ltp?instrument_key=${encodeURIComponent(instrumentKeys)}`;
  const response = await request(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${resolvedToken}`,
    },
    signal: AbortSignal.timeout(8_000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload?.errors?.[0]?.message || payload?.message || `Upstox HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }

  const fetchedAt = new Date().toISOString();
  const quotes = normalizeUpstoxGlobalLtp(payload, { fetchedAt });
  return {
    ok: quotes.length > 0,
    configured: true,
    quotes,
    fetchedAt,
    latencySeconds: 20,
    reason: quotes.length ? null : 'empty_response',
  };
}
