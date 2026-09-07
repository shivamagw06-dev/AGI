/**
 * Yahoo Finance quotes for Market Snapshot / pre-market fallbacks.
 * Covers Indian cash indices, US cash indices, and key commodities.
 */

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

/** Snapshot labels used by the Investment Office Market Snapshot. */
export const YAHOO_INDEX_MAP = [
  // India
  { symbol: '^NSEI', name: 'NIFTY' },
  { symbol: '^NSEBANK', name: 'BANK NIFTY' },
  { symbol: '^BSESN', name: 'SENSEX' },
  { symbol: 'NIFTY_MIDCAP_100.NS', name: 'MIDCAP' },
  { symbol: '^CNXSC', name: 'SMALLCAP' },
  { symbol: '^INDIAVIX', name: 'VIX' },
  // US cash indices (NOT ETF proxies like SPY/QQQ/DIA)
  { symbol: '^GSPC', name: 'S&P' },
  { symbol: '^IXIC', name: 'NASDAQ' },
  { symbol: '^DJI', name: 'Dow' },
  // Commodities / FX
  { symbol: 'GC=F', name: 'Gold' },
  { symbol: 'SI=F', name: 'Silver' },
  { symbol: 'BZ=F', name: 'Brent' },
  { symbol: 'BTC-USD', name: 'Bitcoin' },
  { symbol: 'INR=X', name: 'USDINR' },
];

/** Extra aliases used by pre-market instrument ids. */
export const YAHOO_INSTRUMENT_SYMBOLS = {
  spx: '^GSPC',
  ndx: '^IXIC',
  dji: '^DJI',
  ftse: '^FTSE',
  dax: '^GDAXI',
  nikkei: '^N225',
  hangseng: '^HSI',
  oil: 'CL=F',
  dollar: 'DX-Y.NYB',
  treasury: '^TNX',
  gold: 'GC=F',
  copper: 'HG=F',
  bitcoin: 'BTC-USD',
};

const FX_PAIR_MAP = [
  { symbol: 'INR=X', pair: 'USD/INR', base: 'USD', quote: 'INR', region: 'India', decimals: 4 },
  { symbol: 'EURINR=X', pair: 'EUR/INR', base: 'EUR', quote: 'INR', region: 'India', decimals: 4 },
  { symbol: 'GBPINR=X', pair: 'GBP/INR', base: 'GBP', quote: 'INR', region: 'India', decimals: 4 },
  { symbol: 'EURUSD=X', pair: 'EUR/USD', base: 'EUR', quote: 'USD', region: 'G10', decimals: 4 },
  { symbol: 'GBPUSD=X', pair: 'GBP/USD', base: 'GBP', quote: 'USD', region: 'G10', decimals: 4 },
  { symbol: 'JPY=X', pair: 'USD/JPY', base: 'USD', quote: 'JPY', region: 'G10', decimals: 3 },
  { symbol: 'AUDUSD=X', pair: 'AUD/USD', base: 'AUD', quote: 'USD', region: 'G10', decimals: 4 },
  { symbol: 'NZDUSD=X', pair: 'NZD/USD', base: 'NZD', quote: 'USD', region: 'G10', decimals: 4 },
  { symbol: 'CAD=X', pair: 'USD/CAD', base: 'USD', quote: 'CAD', region: 'G10', decimals: 4 },
  { symbol: 'CHF=X', pair: 'USD/CHF', base: 'USD', quote: 'CHF', region: 'G10', decimals: 4 },
  { symbol: 'CNY=X', pair: 'USD/CNY', base: 'USD', quote: 'CNY', region: 'Asia', decimals: 4 },
  { symbol: 'SGD=X', pair: 'USD/SGD', base: 'USD', quote: 'SGD', region: 'Asia', decimals: 4 },
  { symbol: 'KRW=X', pair: 'USD/KRW', base: 'USD', quote: 'KRW', region: 'Asia', decimals: 2 },
  { symbol: 'IDR=X', pair: 'USD/IDR', base: 'USD', quote: 'IDR', region: 'Asia', decimals: 0 },
  { symbol: 'THB=X', pair: 'USD/THB', base: 'USD', quote: 'THB', region: 'Asia', decimals: 3 },
];

const FX_DRIVER_MAP = [
  { symbol: 'DX-Y.NYB', name: 'Dollar index', unit: 'index', decimals: 2 },
  { symbol: 'BZ=F', name: 'Brent crude', unit: 'USD/bbl', decimals: 2 },
  { symbol: '^TNX', name: 'US 10Y yield', unit: '%', decimals: 3 },
  { symbol: 'GC=F', name: 'Gold', unit: 'USD/oz', decimals: 2 },
];

const FX_CACHE_MS = 5 * 60_000;
let fxIntelligenceCache = null;

function pctFromCloses(price, prevClose) {
  const last = Number(price);
  const prev = Number(prevClose);
  if (!Number.isFinite(last) || !Number.isFinite(prev) || prev === 0) return null;
  return ((last - prev) / prev) * 100;
}

export async function fetchYahooSymbol(symbol) {
  const fetchFn = await ensureFetch();
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=5d`;
  const resp = await fetchFn(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'User-Agent': 'Mozilla/5.0 (compatible; AGIB-UI/1.0)',
    },
    signal: AbortSignal.timeout(10_000),
  });
  if (!resp.ok) return null;
  const json = await resp.json().catch(() => null);
  const result = json?.chart?.result?.[0];
  const meta = result?.meta;
  if (!meta) return null;

  const closes = (result?.indicators?.quote?.[0]?.close || []).filter((x) => x != null);
  const price = Number(meta.regularMarketPrice ?? closes.at(-1));
  const prevClose = Number(closes.length >= 2 ? closes.at(-2) : meta.chartPreviousClose);
  if (!Number.isFinite(price) || price <= 0) return null;

  return {
    price,
    previousClose: Number.isFinite(prevClose) ? prevClose : null,
    percentChange: pctFromCloses(price, prevClose),
    changePct: pctFromCloses(price, prevClose),
    asOf: meta.regularMarketTime
      ? new Date(meta.regularMarketTime * 1000).toISOString()
      : new Date().toISOString(),
    source: 'Yahoo',
    symbol,
  };
}

/**
 * @returns {Promise<Array<{ name: string, price: number, percentChange: number|null, source: string }>>}
 */
export async function fetchYahooIndices(wantedNames = null) {
  const allow = wantedNames
    ? new Set([...wantedNames].map((n) => String(n).toUpperCase()))
    : null;

  const targets = YAHOO_INDEX_MAP.filter((row) => !allow || allow.has(row.name.toUpperCase()));
  const settled = await Promise.allSettled(
    targets.map(async (row) => {
      const quote = await fetchYahooSymbol(row.symbol);
      if (!quote) return null;
      return {
        name: row.name,
        price: quote.price,
        percentChange: quote.percentChange,
        source: 'yahoo',
      };
    })
  );

  return settled
    .map((r) => (r.status === 'fulfilled' ? r.value : null))
    .filter(Boolean);
}

function returnPct(current, previous) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

async function fetchYahooSeries(target) {
  const fetchFn = await ensureFetch();
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(target.symbol)}?interval=1d&range=1mo`;
  const resp = await fetchFn(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'User-Agent': 'Mozilla/5.0 (compatible; AGIB-FX/1.0)',
    },
    signal: AbortSignal.timeout(8_000),
  });
  if (!resp.ok) return null;

  const json = await resp.json().catch(() => null);
  const result = json?.chart?.result?.[0];
  const timestamps = result?.timestamp || [];
  const closes = result?.indicators?.quote?.[0]?.close || [];
  const points = closes
    .map((value, index) => ({
      value: Number(value),
      at: timestamps[index] ? new Date(timestamps[index] * 1000).toISOString() : null,
    }))
    .filter((point) => Number.isFinite(point.value) && point.value > 0);
  if (!points.length) return null;

  const current = points.at(-1).value;
  const prior = (sessions) => points[Math.max(0, points.length - 1 - sessions)]?.value;
  const values = points.map((point) => point.value);
  const asOf = result?.meta?.regularMarketTime
    ? new Date(result.meta.regularMarketTime * 1000).toISOString()
    : points.at(-1).at || new Date().toISOString();

  return {
    ...target,
    price: current,
    asOf,
    source: 'Yahoo Finance',
    latencySeconds: null,
    low: Math.min(...values),
    high: Math.max(...values),
    returns: {
      d1: returnPct(current, prior(1)),
      w1: returnPct(current, prior(5)),
      m1: returnPct(current, points[0].value),
    },
    sparkline: values.slice(-24),
  };
}

async function mapWithConcurrency(items, concurrency, worker) {
  const output = new Array(items.length);
  let cursor = 0;
  async function run() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      output[index] = await worker(items[index]).catch(() => null);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, run));
  return output.filter(Boolean);
}

export function currencyStrength(pairs, horizon) {
  const totals = new Map();
  const add = (currency, value) => {
    const current = totals.get(currency) || { total: 0, observations: 0 };
    current.total += value;
    current.observations += 1;
    totals.set(currency, current);
  };

  pairs.forEach((row) => {
    const move = Number(row?.returns?.[horizon]);
    if (!Number.isFinite(move)) return;
    add(row.base, move);
    add(row.quote, -move);
  });

  return [...totals.entries()]
    .map(([currency, value]) => ({
      currency,
      score: value.observations ? value.total / value.observations : 0,
      observations: value.observations,
    }))
    .sort((a, b) => b.score - a.score);
}

/**
 * Delayed market-reference FX data for the public FX Intelligence page.
 * This is deliberately a read-only observation layer, not an execution feed.
 */
export async function fetchYahooFxIntelligence({ force = false } = {}) {
  const now = Date.now();
  if (!force && fxIntelligenceCache && now - fxIntelligenceCache.at < FX_CACHE_MS) {
    return { ...fxIntelligenceCache.value, cache: 'hit' };
  }

  const [pairs, drivers] = await Promise.all([
    mapWithConcurrency(FX_PAIR_MAP, 4, fetchYahooSeries),
    mapWithConcurrency(FX_DRIVER_MAP, 4, fetchYahooSeries),
  ]);
  const asOf = [...pairs, ...drivers]
    .map((row) => row.asOf)
    .filter(Boolean)
    .sort()
    .at(-1) || new Date().toISOString();

  const value = {
    ok: pairs.length > 0,
    pairs,
    drivers,
    strength: {
      d1: currencyStrength(pairs, 'd1'),
      w1: currencyStrength(pairs, 'w1'),
      m1: currencyStrength(pairs, 'm1'),
    },
    coverage: { available: pairs.length, expected: FX_PAIR_MAP.length },
    asOf,
    source: 'Yahoo Finance market reference',
    delayed: true,
    methodology: 'Returns use available daily closes; currency strength averages signed pair returns.',
    cache: 'miss',
  };
  if (pairs.length) fxIntelligenceCache = { at: now, value };
  return value;
}
