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

export function normalizeUpstoxGlobalCandle(target, payload) {
  const candle = payload?.data?.candles?.[0];
  if (!Array.isArray(candle)) return null;
  const [timestamp, , , , close, volume] = candle;
  const price = finitePositive(close);
  if (!price || !timestamp) return null;
  return {
    ...target,
    price,
    previousClose: null,
    volume: Number.isFinite(Number(volume)) ? Number(volume) : null,
    fetchedAt: timestamp,
    source: 'Upstox Global Indicator',
    latencySeconds: 60,
    quoteMode: '1-minute candle',
  };
}

async function fetchJson(request, url, resolvedToken) {
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
    error.code = payload?.errors?.[0]?.errorCode || payload?.errors?.[0]?.error_code || null;
    throw error;
  }
  return payload;
}

async function fetchIntradayQuote(request, resolvedToken, target) {
  const key = encodeURIComponent(target.instrumentKey);
  const url = `${UPSTOX_V3_BASE}/historical-candle/intraday/${key}/minutes/1`;
  const payload = await fetchJson(request, url, resolvedToken);
  return normalizeUpstoxGlobalCandle(target, payload);
}

export async function fetchUpstoxGlobalFxQuotes({ fetchFn, token } = {}) {
  const resolvedToken = token === undefined ? resolveUpstoxAccessToken().token : String(token || '').trim();
  if (!resolvedToken) {
    return { ok: false, configured: false, quotes: [], reason: 'not_configured' };
  }

  const request = fetchFn || await ensureFetch();
  const instrumentKeys = UPSTOX_GLOBAL_TARGETS.map((target) => target.instrumentKey).join(',');
  const url = `${UPSTOX_V3_BASE}/market-quote/ltp?instrument_key=${encodeURIComponent(instrumentKeys)}`;
  let ltpError = null;
  try {
    const payload = await fetchJson(request, url, resolvedToken);
    const fetchedAt = new Date().toISOString();
    const quotes = normalizeUpstoxGlobalLtp(payload, { fetchedAt });
    if (quotes.length) {
      return {
        ok: true,
        configured: true,
        quotes,
        fetchedAt,
        latencySeconds: 20,
        mode: 'ltp_v3',
        reason: null,
      };
    }
  } catch (error) {
    if (error?.status === 401 || error?.status === 403) throw error;
    ltpError = error;
  }

  const settled = await Promise.allSettled(
    UPSTOX_GLOBAL_TARGETS.map((target) => fetchIntradayQuote(request, resolvedToken, target)),
  );
  const quotes = settled.flatMap((result) => (
    result.status === 'fulfilled' && result.value ? [result.value] : []
  ));
  const fetchedAt = quotes.map((quote) => quote.fetchedAt).filter(Boolean).sort().at(-1) || new Date().toISOString();
  return {
    ok: quotes.length > 0,
    configured: true,
    quotes,
    fetchedAt,
    latencySeconds: quotes.length ? 60 : 20,
    mode: 'intraday_fallback',
    reason: quotes.length === UPSTOX_GLOBAL_TARGETS.length
      ? 'ltp_unavailable'
      : quotes.length
        ? 'partial_intraday_fallback'
        : ltpError?.code === 'UDAPI100095'
          ? 'global_ltp_key_rejected'
          : 'empty_response',
  };
}
