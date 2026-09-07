/**
 * Daily price history from Yahoo's chart endpoint.
 *
 * The snapshot provider next door (yahooIndices.js) returns null for every
 * kind of failure, which is the right shape for a dashboard tile: the tile
 * either has a number or it doesn't. A backfill needs more than that. Being
 * rate limited and being an unknown symbol both produce "no bars", but one
 * must be retried and the other must never be - retrying a delisted ticker
 * for the rest of the run wastes the budget that the live symbols need, and
 * giving up on a throttled one silently leaves a hole in the history. So the
 * outcome is named rather than collapsed to null.
 */

import { barsFromChart } from '../services/dailyBars.js';

const BASE = 'https://query1.finance.yahoo.com/v8/finance/chart';

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

/**
 * Fetch daily bars for one symbol.
 *
 * Returns { status, bars, currency, timeZone, symbol, detail }, where status
 * is one of:
 *   ok         - bars were returned
 *   empty      - the symbol resolved but has no bars in the window
 *   not_found  - Yahoo does not know this symbol; do not retry it
 *   throttled  - rate limited; retry after a pause
 *   failed     - transport or server error; retry
 */
export async function fetchDailyHistory(symbol, { from, to, timeoutMs = 20_000 } = {}) {
  const fetchFn = await ensureFetch();
  const period1 = Math.floor(new Date(from).getTime() / 1000);
  const period2 = Math.floor(new Date(to).getTime() / 1000);
  const url = `${BASE}/${encodeURIComponent(symbol)}`
    + `?interval=1d&period1=${period1}&period2=${period2}&events=div%7Csplit`;

  let resp;
  try {
    resp = await fetchFn(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; AGIB-UI/1.0)',
      },
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    return { status: 'failed', symbol, bars: [], detail: err?.message || 'request failed' };
  }

  // 404 means Yahoo has no such symbol - a permanent answer, not a hiccup.
  if (resp.status === 404) return { status: 'not_found', symbol, bars: [], detail: 'unknown symbol' };
  if (resp.status === 429) return { status: 'throttled', symbol, bars: [], detail: 'rate limited' };
  if (!resp.ok) return { status: 'failed', symbol, bars: [], detail: `http ${resp.status}` };

  const json = await resp.json().catch(() => null);
  // Yahoo also reports an unknown symbol as a 200 with an error body.
  const errCode = json?.chart?.error?.code;
  if (errCode === 'Not Found') return { status: 'not_found', symbol, bars: [], detail: 'unknown symbol' };
  if (errCode) return { status: 'failed', symbol, bars: [], detail: String(errCode) };

  const result = json?.chart?.result?.[0];
  if (!result) return { status: 'failed', symbol, bars: [], detail: 'no result in payload' };

  const bars = barsFromChart(result, { ticker: symbol });
  return {
    status: bars.length ? 'ok' : 'empty',
    symbol,
    bars,
    currency: result?.meta?.currency || null,
    timeZone: result?.meta?.exchangeTimezoneName || null,
    detail: null,
  };
}
