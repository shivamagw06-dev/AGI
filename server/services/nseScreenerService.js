import { budgetedMarketFetch } from '../lib/marketDataBudget.js';
import { loadUpstoxNseIsinMap } from './companyIsinBackfill.js';
import { getResearchUniverse } from './nifty500ResearchService.js';
import { resolveUpstoxAccessToken } from '../providers/upstox.js';

const MASTER_TTL_MS = 24 * 60 * 60 * 1000;
const QUOTE_TTL_MS = 15 * 60 * 1000;
const RETRY_MS = 60 * 1000;
const QUOTE_BATCH_SIZE = 150; // Keep GET URLs well below proxy limits (API maximum is 500).
let masterCache = { items: null, asOf: null, expiresAt: 0, pending: null };
let quoteCache = { quotes: new Map(), asOf: null, expiresAt: 0, pending: null, error: null };

export async function getNseEquityMaster({ force = false } = {}) {
  if (!force && masterCache.items && Date.now() < masterCache.expiresAt) return masterCache;
  if (masterCache.pending) return masterCache.pending;
  masterCache.pending = (async () => {
    try {
      const instruments = await loadUpstoxNseIsinMap();
      if (!instruments.size) throw new Error('NSE equity instrument file is empty.');
      const items = [...instruments].map(([symbol, value]) => ({
        symbol,
        name: value.name || symbol,
        isin: value.isin,
        instrumentKey: value.instrument_key,
      })).sort((a, b) => a.symbol.localeCompare(b.symbol));
      masterCache = { items, asOf: new Date().toISOString(), expiresAt: Date.now() + MASTER_TTL_MS, pending: null };
    } catch (error) {
      if (!masterCache.items || force) throw error;
      masterCache.expiresAt = Date.now() + RETRY_MS;
    }
    return masterCache;
  })();
  try { return await masterCache.pending; }
  finally { masterCache.pending = null; }
}

function finiteNumber(value) {
  const number = Number(value);
  return value === null || value === undefined || value === '' || !Number.isFinite(number) ? null : number;
}

export function normalizeQuote(raw) {
  const lastPrice = finiteNumber(raw?.last_price);
  const previousClose = finiteNumber(raw?.prev_close_price);
  return {
    lastPrice,
    previousClose,
    changePercent: lastPrice != null && previousClose > 0 ? ((lastPrice - previousClose) / previousClose) * 100 : null,
    volume: finiteNumber(raw?.volume),
    yearHigh: finiteNumber(raw?.year_high),
    yearLow: finiteNumber(raw?.year_low),
    quoteTime: raw?.timestamp || null,
  };
}

async function fetchQuoteBatch(batch, token) {
  const keys = batch.map((item) => item.instrumentKey);
  const url = `https://api.upstox.com/v3/market-quote/quotes?instrument_key=${encodeURIComponent(keys.join(','))}`;
  const response = await budgetedMarketFetch('upstox', url, {
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`Upstox quotes HTTP ${response.status}`);
  const body = await response.json();
  if (body.status !== 'success' || !body.data || typeof body.data !== 'object') throw new Error('Invalid Upstox quote response.');
  const quotes = new Map();
  for (const item of batch) {
    const raw = body.data[`NSE_EQ:${item.symbol}`] || body.data[item.instrumentKey.replace('|', ':')];
    if (raw) quotes.set(item.symbol, normalizeQuote(raw));
  }
  return quotes;
}

export async function getNseQuoteSnapshot(items, { force = false } = {}) {
  // Analytics tokens are long-lived and read-only; daily trading tokens remain a fallback.
  const token = String(process.env.UPSTOX_ANALYTICS_TOKEN || '').trim() || resolveUpstoxAccessToken().token;
  if (!token) return { quotes: new Map(), asOf: null, error: 'Market quotes are unavailable until an Upstox analytics or access token is configured.' };
  if (!force && Date.now() < quoteCache.expiresAt) return quoteCache;
  if (quoteCache.pending) return quoteCache.pending;
  quoteCache.pending = (async () => {
    const batches = [];
    for (let index = 0; index < items.length; index += QUOTE_BATCH_SIZE) batches.push(items.slice(index, index + QUOTE_BATCH_SIZE));
    const settled = [];
    for (let index = 0; index < batches.length; index += 3) {
      settled.push(...await Promise.allSettled(batches.slice(index, index + 3).map((batch) => fetchQuoteBatch(batch, token))));
    }
    const quotes = new Map();
    for (const result of settled) {
      if (result.status === 'fulfilled') for (const [symbol, quote] of result.value) quotes.set(symbol, quote);
    }
    const failed = settled.filter((result) => result.status === 'rejected');
    if (quotes.size) {
      quoteCache = {
        quotes,
        asOf: new Date().toISOString(),
        expiresAt: Date.now() + (failed.length ? RETRY_MS : QUOTE_TTL_MS),
        pending: null,
        error: failed.length ? `${failed.length} of ${batches.length} quote batches were unavailable.` : null,
      };
    } else {
      quoteCache.expiresAt = Date.now() + RETRY_MS;
      quoteCache.error = failed[0]?.reason?.message || 'Market quotes are currently unavailable.';
    }
    return quoteCache;
  })();
  try { return await quoteCache.pending; }
  finally { quoteCache.pending = null; }
}

export async function getNseScreenerUniverse({ force = false } = {}) {
  const master = await getNseEquityMaster({ force });
  const [researchResult, quoteResult] = await Promise.allSettled([
    getResearchUniverse(),
    getNseQuoteSnapshot(master.items, { force }),
  ]);
  const research = researchResult.status === 'fulfilled' ? researchResult.value : { run: null, items: [] };
  const snapshot = quoteResult.status === 'fulfilled' ? quoteResult.value : { quotes: new Map(), asOf: null, error: 'Market quotes are currently unavailable.' };
  const researchBySymbol = new Map(research.items.map((item) => [item.symbol, item]));
  return {
    run: research.run,
    instrumentAsOf: master.asOf,
    quotesAsOf: snapshot.asOf,
    quoteCount: snapshot.quotes.size,
    quoteError: snapshot.error,
    researchCount: research.items.length,
    items: master.items.map((item) => ({
      ...item,
      ...(researchBySymbol.get(item.symbol) || {}),
      hasResearch: researchBySymbol.has(item.symbol),
      ...(snapshot.quotes.get(item.symbol) || {}),
    })),
  };
}

export function clearNseScreenerCache() {
  masterCache = { items: null, asOf: null, expiresAt: 0, pending: null };
  quoteCache = { quotes: new Map(), asOf: null, expiresAt: 0, pending: null, error: null };
}
