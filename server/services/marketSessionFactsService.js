/**
 * Session facts pack for AGI Market Explained notes.
 * Collects index levels, movers with prices/%, and top company posts
 * so summaries can cite numbers and rephrase source material in AGI style.
 */

import { fetchGrowwTicker, isGrowwConfigured } from '../providers/groww.js';
import { fetchTrending } from '../providers/fallback.js';

const CACHE_MS = 10 * 60 * 1000;
const MAX_MOVERS = 5;
const MAX_POSTS = 8;

let cache = null;
let expiresAt = 0;
let inflight = null;

function num(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function fmtPrice(value) {
  const n = num(value);
  if (n == null) return null;
  return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function fmtPct(value) {
  const n = num(value);
  if (n == null) return null;
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function normalizeMover(row = {}) {
  const symbol = String(row.ticker || row.symbol || row.company_name || row.company || '')
    .split(' ')[0]
    .toUpperCase()
    .replace(/[^A-Z0-9&-]/g, '');
  if (!symbol) return null;
  const price = num(row.price ?? row.ltp ?? row.last_price ?? row.close);
  const percentChange = num(row.percent_change ?? row.percentChange ?? row.change_percent ?? row.change);
  return {
    symbol,
    name: row.company_name || row.company || row.name || symbol,
    price,
    priceLabel: fmtPrice(price),
    percentChange,
    percentLabel: fmtPct(percentChange),
  };
}

async function fetchCompanyPosts(symbols, apiKey, baseUrl) {
  const unique = [...new Set(symbols)].slice(0, 6);
  const posts = [];
  for (const symbol of unique) {
    try {
      const url = new URL(`${baseUrl}/recent_announcements`);
      url.searchParams.set('stock_name', symbol);
      const response = await fetch(url, {
        headers: { Accept: 'application/json', 'x-api-key': apiKey },
        signal: AbortSignal.timeout(12_000),
      });
      if (!response.ok) continue;
      const payload = await response.json();
      const items = Array.isArray(payload) ? payload : [];
      for (const item of items.slice(0, 2)) {
        const title = item.title || item.headline || item.subject;
        if (!title) continue;
        posts.push({
          symbol,
          title: String(title),
          date: item.date || null,
          url: item.link || item.url || null,
          window: /pre.?market|open|start|sod/i.test(String(title))
            ? 'Start of day'
            : /close|eod|result|earnings|q[1-4]/i.test(String(title))
              ? 'End of day / results'
              : 'Company update',
        });
      }
    } catch {
      /* skip symbol */
    }
  }
  return posts.slice(0, MAX_POSTS);
}

function emptyFacts() {
  return {
    session: 'Market session facts',
    updatedAt: new Date().toISOString(),
    indices: [],
    gainers: [],
    losers: [],
    companyPosts: [],
    unavailable: true,
  };
}

async function fetchNseIndices() {
  try {
    const response = await fetch('https://www.nseindia.com/api/allIndices', {
      headers: {
        Accept: 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; AGIB-Briefing/1.0)',
        Referer: 'https://www.nseindia.com/',
      },
      signal: AbortSignal.timeout(12_000),
    });
    if (!response.ok) return [];
    const payload = await response.json();
    const wanted = new Map([
      ['NIFTY 50', 'Nifty 50'],
      ['NIFTY BANK', 'Bank Nifty'],
      ['INDIA VIX', 'India VIX'],
    ]);
    const rows = Array.isArray(payload?.data) ? payload.data : [];
    return rows
      .map((row) => {
        const rawName = String(row.index || row.indexSymbol || '').trim().toUpperCase();
        const name = wanted.get(rawName);
        if (!name) return null;
        const price = num(row.last ?? row.previousClose);
        const percentChange = num(row.percentChange ?? row.variation);
        return {
          name,
          price,
          priceLabel: fmtPrice(price),
          percentChange,
          percentLabel: fmtPct(percentChange),
        };
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

export async function getMarketSessionFacts() {
  if (cache && expiresAt > Date.now()) return cache;
  if (inflight) return inflight;

  inflight = (async () => {
    try {
      const apiKey = (process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || '').trim();
      const baseUrl = (process.env.INDIANAPI_BASE || 'https://stock.indianapi.in').replace(/\/$/, '');

      const [ticker, trending, nseIndices] = await Promise.all([
        isGrowwConfigured() ? fetchGrowwTicker().catch(() => []) : Promise.resolve([]),
        fetchTrending(apiKey, baseUrl),
        fetchNseIndices(),
      ]);

      let indices = (ticker || [])
        .filter((row) => (row?.name || row?.label) && row.price != null)
        .map((row) => ({
          name: row.name || row.label,
          price: num(row.price),
          priceLabel: fmtPrice(row.price),
          percentChange: num(row.percentChange),
          percentLabel: fmtPct(row.percentChange),
        }));
      if (!indices.length) indices = nseIndices;

      const gainers = (trending.gainers || []).map(normalizeMover).filter(Boolean).slice(0, MAX_MOVERS);
      const losers = (trending.losers || []).map(normalizeMover).filter(Boolean).slice(0, MAX_MOVERS);
      const focusSymbols = [...gainers, ...losers].map((item) => item.symbol);
      const companyPosts = apiKey
        ? await fetchCompanyPosts(focusSymbols, apiKey, baseUrl)
        : [];

      const value = {
        session: 'Market session facts',
        updatedAt: new Date().toISOString(),
        indices,
        gainers,
        losers,
        companyPosts,
        unavailable: !indices.length && !gainers.length && !losers.length,
      };
      cache = value;
      expiresAt = Date.now() + CACHE_MS;
      return value;
    } catch (error) {
      console.warn('[session-facts]', error.message);
      return cache || emptyFacts();
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}
