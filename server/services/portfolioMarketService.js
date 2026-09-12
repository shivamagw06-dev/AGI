import { getHistoricalCandles, getQuote } from '../providers/groww.js';
import { getCorporateActions } from '../providers/upstox.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

const CACHE_MS = 15 * 60 * 1000;
const MAX_INSTRUMENTS = 40;
const cache = new Map();

function clean(value, fallback = '') {
  return String(value ?? fallback).trim();
}

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function isoDate(value) {
  const parsed = typeof value === 'number' && value < 10_000_000_000 ? value * 1000 : value;
  const date = new Date(parsed);
  return Number.isFinite(date.getTime()) ? date.toISOString().slice(0, 10) : null;
}

function toReturns(prices) {
  return prices.slice(1).map((row, index) => {
    const prior = prices[index]?.close;
    return {
      date: row.date,
      returnPct: prior > 0 ? ((row.close / prior) - 1) * 100 : null,
    };
  }).filter((row) => row.date && Number.isFinite(row.returnPct));
}

function growwPrices(candles) {
  return (candles || []).map((row) => ({
    date: isoDate(row?.[0]),
    close: number(row?.[4]),
  })).filter((row) => row.date && row.close > 0).sort((a, b) => a.date.localeCompare(b.date));
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: { Accept: 'application/json', 'User-Agent': 'AGI-Portfolio-Intelligence/1.0' },
    signal: AbortSignal.timeout(8_000),
  });
  if (!response.ok) throw new Error(`market request failed (${response.status})`);
  return response.json();
}

async function yahooSeries(symbol, days) {
  const period1 = Math.floor((Date.now() - days * 86_400_000) / 1000);
  const period2 = Math.floor(Date.now() / 1000) + 86_400;
  const url = new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`);
  url.searchParams.set('period1', String(period1));
  url.searchParams.set('period2', String(period2));
  url.searchParams.set('interval', '1d');
  url.searchParams.set('events', 'div,splits');
  const body = await fetchJson(url);
  const result = body?.chart?.result?.[0];
  if (!result) throw new Error(body?.chart?.error?.description || 'Yahoo series unavailable');
  const closes = result?.indicators?.quote?.[0]?.close || [];
  const prices = (result.timestamp || []).map((timestamp, index) => ({
    date: isoDate(timestamp),
    close: number(closes[index]),
  })).filter((row) => row.date && row.close > 0);
  const latest = number(result?.meta?.regularMarketPrice) || prices.at(-1)?.close || null;
  const prior = number(result?.meta?.chartPreviousClose) || prices.at(-2)?.close || null;
  return {
    price: latest,
    changePct: latest && prior ? ((latest / prior) - 1) * 100 : null,
    currency: result?.meta?.currency || null,
    asOf: result?.meta?.regularMarketTime ? new Date(result.meta.regularMarketTime * 1000).toISOString() : null,
    prices,
    events: result?.events || {},
    source: 'yahoo_chart',
    quality: 'observed',
  };
}

function yahooSymbol(instrument) {
  const symbol = clean(instrument.symbol).toUpperCase();
  const market = clean(instrument.market).toUpperCase();
  if (instrument.currency === 'USD' || ['NASDAQ', 'NYSE', 'NYSEARCA', 'US'].includes(market)) return symbol;
  if (market === 'BSE') return `${symbol}.BO`;
  if (market === 'NSE' || instrument.asset_type === 'indian_stock' || instrument.asset_type === 'etf') return `${symbol}.NS`;
  return symbol;
}

function quotePrice(quote) {
  return number(quote?.last_price ?? quote?.ltp ?? quote?.current_price ?? quote?.price ?? quote?.close);
}

async function indianSeries(instrument, days) {
  const exchange = clean(instrument.market, 'NSE').toUpperCase() === 'BSE' ? 'BSE' : 'NSE';
  const symbol = clean(instrument.symbol).toUpperCase();
  const [quoteResult, historyResult] = await Promise.allSettled([
    getQuote(exchange, 'CASH', symbol),
    getHistoricalCandles(exchange, 'CASH', symbol, days),
  ]);
  const prices = historyResult.status === 'fulfilled' ? growwPrices(historyResult.value) : [];
  const latest = quoteResult.status === 'fulfilled' ? quotePrice(quoteResult.value) : prices.at(-1)?.close || null;
  if (!latest && !prices.length) return yahooSeries(yahooSymbol(instrument), days);
  const prior = prices.at(-2)?.close || null;
  return {
    price: latest,
    changePct: latest && prior ? ((latest / prior) - 1) * 100 : null,
    currency: 'INR',
    asOf: new Date().toISOString(),
    prices,
    events: {},
    source: quoteResult.status === 'fulfilled' ? 'groww_live' : 'groww_history',
    quality: quoteResult.status === 'fulfilled' ? 'live' : 'observed',
  };
}

async function instrumentSeries(instrument, days) {
  const key = `${clean(instrument.market)}:${clean(instrument.symbol)}:${days}`.toUpperCase();
  const hit = cache.get(key);
  if (hit && hit.expiresAt > Date.now()) return hit.value;

  if (instrument.asset_type === 'cash') {
    return {
      price: number(instrument.current_price) ?? 1,
      changePct: 0,
      currency: instrument.currency || 'INR',
      asOf: new Date().toISOString(),
      returns: [],
      prices: [],
      source: 'portfolio_ledger',
      quality: 'declared',
    };
  }

  let result;
  if (instrument.asset_type === 'mutual_fund' || clean(instrument.market).toUpperCase() === 'AMFI') {
    result = {
      price: number(instrument.current_price),
      changePct: null,
      currency: instrument.currency || 'INR',
      asOf: instrument.price_as_of || null,
      prices: [],
      events: {},
      source: instrument.price_source || 'manual_nav',
      quality: 'manual',
    };
  } else if (instrument.currency === 'USD') {
    result = await yahooSeries(yahooSymbol(instrument), days);
  } else {
    result = await indianSeries(instrument, days);
  }

  const value = { ...result, returns: toReturns(result.prices || []) };
  cache.set(key, { value, expiresAt: Date.now() + CACHE_MS });
  return value;
}

async function yahooNews(instruments) {
  const terms = instruments.filter((row) => row.asset_type !== 'cash').slice(0, 12);
  const seen = new Set();
  const rows = [];
  await Promise.all(terms.map(async (instrument) => {
    try {
      const body = await fetchJson(`https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(instrument.symbol)}&quotesCount=1&newsCount=3`);
      for (const item of body?.news || []) {
        const key = item.uuid || item.link;
        if (!key || seen.has(key)) continue;
        seen.add(key);
        rows.push({
          eventKey: `yahoo:${key}`,
          eventType: 'news',
          symbol: instrument.symbol,
          title: item.title,
          source: item.publisher || 'Yahoo Finance',
          sourceUrl: item.link,
          occurredAt: item.providerPublishTime ? new Date(item.providerPublishTime * 1000).toISOString() : null,
          severity: 'info',
        });
      }
    } catch {
      // News is optional; price and risk calculations remain usable.
    }
  }));
  return rows.sort((a, b) => Date.parse(b.occurredAt || 0) - Date.parse(a.occurredAt || 0)).slice(0, 24);
}

async function yahooFundamentals(instruments) {
  const eligible = instruments.filter((row) => row.asset_type !== 'cash' && row.asset_type !== 'mutual_fund');
  if (!eligible.length) return {};
  try {
    const symbols = eligible.map(yahooSymbol);
    const body = await fetchJson(`https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(symbols.join(','))}`);
    const bySymbol = new Map((body?.quoteResponse?.result || []).map((row) => [clean(row.symbol).toUpperCase(), row]));
    return Object.fromEntries(eligible.map((instrument) => {
      const row = bySymbol.get(yahooSymbol(instrument).toUpperCase()) || {};
      return [instrument.clientKey, {
        marketCap: number(row.marketCap),
        trailingPe: number(row.trailingPE),
        forwardPe: number(row.forwardPE),
        priceToBook: number(row.priceToBook),
        trailingEps: number(row.epsTrailingTwelveMonths),
        dividendYield: number(row.trailingAnnualDividendYield),
        fiftyTwoWeekChangePct: number(row.fiftyTwoWeekChangePercent),
        fiftyTwoWeekHigh: number(row.fiftyTwoWeekHigh),
        fiftyTwoWeekLow: number(row.fiftyTwoWeekLow),
        averageVolume: number(row.averageDailyVolume3Month),
        source: 'yahoo_quote',
      }];
    }));
  } catch {
    return {};
  }
}

async function corporateActions(instruments) {
  const rows = [];
  for (const instrument of instruments.filter((row) => row.isin).slice(0, 12)) {
    try {
      const payload = await getCorporateActions(instrument.isin);
      for (const item of payload?.data || payload?.corporate_actions || []) {
        rows.push({
          eventKey: `upstox:${instrument.isin}:${item.id || item.ex_date || item.record_date || JSON.stringify(item)}`,
          eventType: 'corporate_action',
          symbol: instrument.symbol,
          title: item.description || item.action_type || item.type || 'Corporate action',
          occurredAt: item.ex_date || item.record_date || item.announcement_date || null,
          source: 'Upstox corporate actions',
          severity: 'watch',
          metadata: item,
        });
      }
    } catch {
      // The ISIN may not be covered by Upstox. Keep the rest of the package.
    }
  }
  return rows;
}

async function persistTrustedReferenceData(benchmarks, fx) {
  const supabase = createSupabaseAdmin();
  if (!supabase) return;
  try {
    // This endpoint accepts user-entered symbols. Never promote request data
    // into the shared instrument registry. Only controlled provider reference
    // series (benchmarks and FX) are persisted from this path.
    for (const [symbol, result] of Object.entries(benchmarks)) {
      if (!result?.prices?.length) continue;
      await supabase.from('portfolio_benchmark_prices').upsert(result.prices.slice(-750).map((row) => ({
        benchmark_symbol: symbol,
        price_date: row.date,
        close_price: row.close,
        currency: result.currency || 'INR',
        source: result.source,
        source_as_of: result.asOf,
      })), { onConflict: 'benchmark_symbol,price_date,source' });
    }
    if (fx?.prices?.length) {
      await supabase.from('portfolio_fx_rates').upsert(fx.prices.slice(-750).map((row) => ({
        base_currency: 'USD', quote_currency: 'INR', rate_date: row.date,
        rate: row.close, source: fx.source, source_as_of: fx.asOf,
      })), { onConflict: 'base_currency,quote_currency,rate_date,source' });
    }
  } catch (error) {
    console.warn('[portfolio-market] reference persistence skipped:', error.message);
  }
}

export async function getPortfolioMarketPackage({ instruments = [], days = 400 } = {}) {
  const safeDays = Math.max(60, Math.min(Number(days) || 400, 1_900));
  const safeInstruments = instruments.slice(0, MAX_INSTRUMENTS).map((row, index) => ({
    clientKey: clean(row.id, `${index}:${row.symbol}`),
    symbol: clean(row.symbol).toUpperCase(),
    asset_name: clean(row.asset_name, row.symbol),
    asset_type: clean(row.asset_type, 'indian_stock'),
    market: clean(row.market, 'NSE').toUpperCase(),
    currency: clean(row.currency, 'INR').toUpperCase(),
    current_price: row.current_price,
    price_as_of: row.price_as_of,
    price_source: row.price_source,
    country: clean(row.country),
    sector: clean(row.sector),
    isin: clean(row.isin),
    provider_key: clean(row.provider_key),
  })).filter((row) => row.symbol);

  const settled = await Promise.all(safeInstruments.map(async (instrument) => {
    try {
      return [instrument.clientKey, await instrumentSeries(instrument, safeDays)];
    } catch (error) {
      return [instrument.clientKey, {
        price: number(instrument.current_price), returns: [], prices: [],
        source: instrument.price_source || 'manual_fallback', quality: 'stale_or_manual',
        error: error.message,
      }];
    }
  }));
  const results = Object.fromEntries(settled);
  const [nifty, sp500, fx, news, actions, fundamentals] = await Promise.all([
    yahooSeries('^NSEI', safeDays).catch(() => ({ prices: [], returns: [], source: 'unavailable' })),
    yahooSeries('^GSPC', safeDays).catch(() => ({ prices: [], returns: [], source: 'unavailable' })),
    yahooSeries('INR=X', safeDays).catch(() => ({ prices: [], returns: [], source: 'unavailable' })),
    yahooNews(safeInstruments),
    corporateActions(safeInstruments),
    yahooFundamentals(safeInstruments),
  ]);
  Object.entries(fundamentals).forEach(([clientKey, value]) => {
    if (results[clientKey]) results[clientKey] = { ...results[clientKey], fundamentals: value };
  });
  const benchmarks = {
    NIFTY: { ...nifty, returns: toReturns(nifty.prices || []) },
    '^GSPC': { ...sp500, returns: toReturns(sp500.prices || []) },
  };
  const fxSeries = { ...fx, returns: toReturns(fx.prices || []) };
  void persistTrustedReferenceData(benchmarks, fxSeries);

  return {
    ok: true,
    instruments: results,
    benchmarks,
    fx: { usdInr: fxSeries },
    events: [...actions, ...news].sort((a, b) => Date.parse(b.occurredAt || 0) - Date.parse(a.occurredAt || 0)),
    coverage: {
      requested: safeInstruments.length,
      liveOrObserved: Object.values(results).filter((row) => ['live', 'observed'].includes(row.quality)).length,
      manualOrUnavailable: Object.values(results).filter((row) => !['live', 'observed'].includes(row.quality)).length,
    },
    generatedAt: new Date().toISOString(),
  };
}
