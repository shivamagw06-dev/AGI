/**
 * World stocks board — delayed Yahoo cash/futures reference for AGI /markets/stocks.
 * Not an exchange feed and not a Bloomberg redistribution.
 */

const CACHE_MS = 5 * 60_000;
const CHART_RANGE = '1y';
const MIN_YEAR_SPAN_DAYS = 200;
const MIN_MONTH_SPAN_DAYS = 15;
const HISTORY_POINTS = 64;
const CONCURRENCY = 4;

export const STOCKS_BOARD_INSTRUMENTS = [
  // Futures
  { id: 'es', ticker: 'ES1', name: 'E-mini S&P 500', yahoo: 'ES=F', region: 'futures' },
  { id: 'nq', ticker: 'NQ1', name: 'E-mini Nasdaq-100', yahoo: 'NQ=F', region: 'futures' },
  { id: 'ym', ticker: 'YM1', name: 'Mini-Sized Dow', yahoo: 'YM=F', region: 'futures' },
  { id: 'rty', ticker: 'RTY1', name: 'E-mini Russell 2000', yahoo: 'RTY=F', region: 'futures' },
  { id: 'nkd', ticker: 'NKD1', name: 'Nikkei 225 USD', yahoo: 'NKD=F', region: 'futures' },
  // Americas
  { id: 'dji', ticker: 'DJI', name: 'Dow Jones Industrial Average', yahoo: '^DJI', region: 'americas' },
  { id: 'gspc', ticker: 'SPX', name: 'S&P 500', yahoo: '^GSPC', region: 'americas' },
  { id: 'ixic', ticker: 'CCMP', name: 'Nasdaq Composite', yahoo: '^IXIC', region: 'americas' },
  { id: 'nya', ticker: 'NYA', name: 'NYSE Composite', yahoo: '^NYA', region: 'americas' },
  { id: 'gsptse', ticker: 'SPTSX', name: 'S&P/TSX Composite', yahoo: '^GSPTSE', region: 'americas' },
  // EMEA
  { id: 'stoxx50', ticker: 'SX5E', name: 'Euro Stoxx 50', yahoo: '^STOXX50E', region: 'emea' },
  { id: 'ftse', ticker: 'UKX', name: 'FTSE 100', yahoo: '^FTSE', region: 'emea' },
  { id: 'dax', ticker: 'DAX', name: 'DAX', yahoo: '^GDAXI', region: 'emea' },
  { id: 'cac', ticker: 'CAC', name: 'CAC 40', yahoo: '^FCHI', region: 'emea' },
  { id: 'ibex', ticker: 'IBEX', name: 'IBEX 35', yahoo: '^IBEX', region: 'emea' },
  // Asia Pacific
  { id: 'n225', ticker: 'NKY', name: 'Nikkei 225', yahoo: '^N225', region: 'apac' },
  {
    id: 'topx',
    ticker: '1306',
    name: 'TOPIX',
    yahoo: '1306.T',
    region: 'apac',
    proxy: true,
    proxyNote: 'NEXT FUNDS TOPIX ETF used as a delayed proxy; Yahoo has no live TOPIX cash series.',
  },
  { id: 'hsi', ticker: 'HSI', name: 'Hang Seng', yahoo: '^HSI', region: 'apac' },
  { id: 'csi300', ticker: 'SHSZ300', name: 'CSI 300', yahoo: '000300.SS', region: 'apac' },
  { id: 'axjo', ticker: 'AS51', name: 'S&P/ASX 200', yahoo: '^AXJO', region: 'apac' },
  {
    id: 'msci-apac',
    ticker: 'IPAC',
    name: 'MSCI Pacific',
    yahoo: 'IPAC',
    region: 'apac',
    proxy: true,
    proxyNote: 'iShares Core MSCI Pacific ETF used as a delayed proxy; not the MSCI AC Asia Pacific cash index.',
  },
  // India (AGI addition — Bloomberg's stocks board has no India table)
  { id: 'nsei', ticker: 'NSEI', name: 'Nifty 50', yahoo: '^NSEI', region: 'india' },
  { id: 'bsesn', ticker: 'SENSEX', name: 'S&P BSE Sensex', yahoo: '^BSESN', region: 'india' },
  { id: 'banknifty', ticker: 'BANKNIFTY', name: 'Nifty Bank', yahoo: '^NSEBANK', region: 'india' },
  { id: 'midcap', ticker: 'NIFTYMID', name: 'Nifty Midcap 100', yahoo: 'NIFTY_MIDCAP_100.NS', region: 'india' },
  { id: 'nifty200', ticker: 'CNX200', name: 'Nifty 200', yahoo: '^CNX200', region: 'india' },
  { id: 'indiavix', ticker: 'INDIAVIX', name: 'India VIX', yahoo: '^INDIAVIX', region: 'india' },
];

export const REGION_META = [
  { id: 'futures', title: 'Futures', blurb: 'Front-month equity index futures. Session times follow the listing venue.' },
  { id: 'americas', title: 'Americas', blurb: 'US and Canada cash indices.' },
  { id: 'emea', title: 'Europe, Middle East & Africa', blurb: 'Europe cash indices. No licensed Stoxx/FTSE redistribution — delayed Yahoo reference.' },
  { id: 'apac', title: 'Asia Pacific', blurb: 'Japan, China, Hong Kong and Australia cash indices. TOPIX and MSCI Pacific are delayed ETF proxies.' },
  { id: 'india', title: 'India', blurb: 'NSE and BSE cash indices. AGI home tape; still delayed via Yahoo on this board.' },
];

export const POPULAR_IDS = ['nsei', 'bsesn', 'gspc', 'ixic', 'dji', 'n225', 'ftse', 'dax', 'hsi'];
export const COMPARE_DEFAULT_IDS = ['nsei', 'gspc', 'ixic'];

let cache = null;

export function resetStocksBoardCache() {
  cache = null;
}

export function pctReturn(current, previous) {
  if (current == null || previous == null || previous === '') return null;
  const last = Number(current);
  const prev = Number(previous);
  if (!Number.isFinite(last) || !Number.isFinite(prev) || prev === 0) return null;
  return ((last - prev) / prev) * 100;
}

export function closesFromChart(json) {
  const result = json?.chart?.result?.[0];
  if (!result) return [];
  const timestamps = result.timestamp || [];
  const closes = result.indicators?.quote?.[0]?.close || [];
  const points = [];
  for (let i = 0; i < closes.length; i += 1) {
    const value = Number(closes[i]);
    const ts = Number(timestamps[i]);
    if (!Number.isFinite(value) || value <= 0 || !Number.isFinite(ts)) continue;
    points.push({ t: ts * 1000, v: value });
  }
  return points;
}

function closestOnOrBefore(closes, targetMs) {
  let found = null;
  for (const point of closes) {
    if (point.t <= targetMs) found = point;
    else break;
  }
  return found;
}

export function round(value, digits = 2) {
  if (value == null || value === '') return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}

function utcDay(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

export function previousSessionClose(closes, liveTs) {
  if (!Array.isArray(closes) || !closes.length) return null;
  const lastBar = closes.at(-1);
  const previousBar = closes.at(-2);
  const sessionDay = liveTs ? utcDay(liveTs) : utcDay(lastBar.t);
  if (sessionDay === utcDay(lastBar.t)) {
    return previousBar ? previousBar.v : null;
  }
  return lastBar.v;
}

export function horizonReturn(closes, lastPrice, daysBack, minSpanDays) {
  if (!Array.isArray(closes) || !closes.length) return null;
  const last = Number(lastPrice);
  if (!Number.isFinite(last)) return null;
  const lastTs = closes[closes.length - 1].t;
  const target = lastTs - daysBack * 86_400_000;
  let prior = closestOnOrBefore(closes, target);
  const spanDays = (lastTs - closes[0].t) / 86_400_000;
  if (!prior && spanDays >= minSpanDays) prior = closes[0];
  if (!prior) return null;
  if ((lastTs - prior.t) / 86_400_000 < minSpanDays) return null;
  return pctReturn(last, prior.v);
}

export function downsampleHistory(closes, maxPoints = HISTORY_POINTS) {
  if (!Array.isArray(closes) || closes.length === 0) return [];
  if (closes.length <= maxPoints) {
    return closes.map((point) => ({ t: new Date(point.t).toISOString().slice(0, 10), v: round(point.v, 4) }));
  }
  const lastIndex = closes.length - 1;
  const step = lastIndex / (maxPoints - 1);
  const picked = [];
  const seen = new Set();
  for (let i = 0; i < maxPoints; i += 1) {
    const index = Math.min(lastIndex, Math.round(i * step));
    if (seen.has(index)) continue;
    seen.add(index);
    const point = closes[index];
    picked.push({ t: new Date(point.t).toISOString().slice(0, 10), v: round(point.v, 4) });
  }
  return picked;
}

export function formatSessionTime(iso, timeZone) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  try {
    return new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: timeZone || 'UTC',
      timeZoneName: 'short',
    }).format(date);
  } catch {
    return date.toISOString().slice(11, 16) + ' UTC';
  }
}

export function assembleInstrumentRow(instrument, json) {
  const result = json?.chart?.result?.[0];
  const meta = result?.meta;
  const closes = closesFromChart(json);
  if (!meta && !closes.length) {
    return unavailableRow(instrument, 'chart_empty');
  }

  const lastClose = closes.at(-1)?.v;
  const last = Number(meta?.regularMarketPrice ?? lastClose);
  if (!Number.isFinite(last) || last <= 0) return unavailableRow(instrument, 'no_last');

  const liveTs = meta?.regularMarketTime ? meta.regularMarketTime * 1000 : closes.at(-1)?.t;
  // Yahoo chartPreviousClose on range=1y is the first print in the window, not yesterday.
  const previous = previousSessionClose(closes, liveTs);
  const change = previous == null ? null : last - previous;
  const asOf = liveTs ? new Date(liveTs).toISOString() : null;

  return {
    id: instrument.id,
    ticker: instrument.ticker,
    name: instrument.name,
    yahoo: instrument.yahoo,
    region: instrument.region,
    last: round(last, 2),
    change: change == null ? null : round(change, 2),
    changePct: round(pctReturn(last, previous), 2),
    monthPct: round(horizonReturn(closes, last, 30, MIN_MONTH_SPAN_DAYS), 2),
    yearPct: round(horizonReturn(closes, last, 365, MIN_YEAR_SPAN_DAYS), 2),
    asOf,
    timeLabel: formatSessionTime(asOf, meta?.exchangeTimezoneName || meta?.timezone),
    timeZone: meta?.exchangeTimezoneName || meta?.timezone || null,
    delayed: true,
    proxy: Boolean(instrument.proxy),
    proxyNote: instrument.proxyNote || null,
    available: true,
    history: downsampleHistory(closes),
    source: 'Yahoo Finance',
  };
}

function unavailableRow(instrument, reason) {
  return {
    id: instrument.id,
    ticker: instrument.ticker,
    name: instrument.name,
    yahoo: instrument.yahoo,
    region: instrument.region,
    last: null,
    change: null,
    changePct: null,
    monthPct: null,
    yearPct: null,
    asOf: null,
    timeLabel: null,
    timeZone: null,
    delayed: true,
    proxy: Boolean(instrument.proxy),
    proxyNote: instrument.proxyNote || null,
    available: false,
    history: [],
    reason,
    source: 'unavailable',
  };
}

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

async function fetchChart(yahoo, fetchFn) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(yahoo)}?interval=1d&range=${CHART_RANGE}&includePrePost=false`;
  const resp = await fetchFn(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'User-Agent': 'Mozilla/5.0 (compatible; AGIB-StocksBoard/1.0)',
    },
    signal: AbortSignal.timeout(10_000),
  });
  if (!resp.ok) return null;
  const json = await resp.json().catch(() => null);
  if (!json?.chart?.result?.[0]) return null;
  return json;
}

async function mapWithConcurrency(items, concurrency, worker) {
  const output = new Array(items.length);
  let cursor = 0;
  async function run() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      output[index] = await worker(items[index]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, run));
  return output;
}

export function groupBoardRows(rows) {
  const regions = {};
  for (const meta of REGION_META) {
    regions[meta.id] = {
      ...meta,
      rows: rows.filter((row) => row.region === meta.id),
    };
  }
  const popular = POPULAR_IDS.map((id) => rows.find((row) => row.id === id)).filter(Boolean);
  return { regions, popular };
}

export async function getStocksBoard({ force = false, fetchFn } = {}) {
  const now = Date.now();
  if (!force && cache && now - cache.at < CACHE_MS) {
    return { ...cache.value, cache: 'hit' };
  }

  const fetchImpl = fetchFn || (await ensureFetch());
  const rows = await mapWithConcurrency(STOCKS_BOARD_INSTRUMENTS, CONCURRENCY, async (instrument) => {
    try {
      const json = await fetchChart(instrument.yahoo, fetchImpl);
      if (!json) return unavailableRow(instrument, 'upstream_empty');
      return assembleInstrumentRow(instrument, json);
    } catch (error) {
      console.warn(`[stocks-board] ${instrument.id}:`, error?.message || error);
      return unavailableRow(instrument, 'upstream_error');
    }
  });

  const available = rows.filter((row) => row.available).length;
  const { regions, popular } = groupBoardRows(rows);
  const asOf = rows
    .map((row) => row.asOf)
    .filter(Boolean)
    .sort()
    .at(-1) || new Date().toISOString();

  const value = {
    ok: available > 0,
    delayed: true,
    source: 'Yahoo Finance market reference',
    asOf,
    available,
    expected: STOCKS_BOARD_INSTRUMENTS.length,
    cache: 'miss',
    methodology:
      'Last and day change use Yahoo regular-session last vs previous close. 1M and 1Y are total return vs the last available daily close on or before 30 / 365 calendar days. A 1Y figure is withheld unless the series spans at least 200 days. Quotes are delayed. Not NSE/BSE/CME official. Not Bloomberg.',
    compareDefault: COMPARE_DEFAULT_IDS,
    popular,
    regions,
  };

  if (available > 0) cache = { at: now, value };
  return value;
}
