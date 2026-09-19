/**
 * Unified market data service — Groww primary, NSE/IndianAPI fallback.
 * Provider-agnostic layer for frontend consumption.
 */

import { isGrowwConfigured, fetchGrowwTicker } from '../providers/groww.js';
import { fetchNseIndices, fetchCommodities, fetchTrending } from '../providers/fallback.js';
import { oncePerMarketCycle } from '../config/marketRefresh.js';
import { computeMarketOutlook, computeMarketPulse } from './marketOutlookEngine.js';

let growwBackoffUntil = 0;

function findIndex(rows, ...names) {
  const set = new Set(names.map((n) => n.toUpperCase()));
  return rows.find((r) => set.has(String(r.name).toUpperCase())) || null;
}

function normalizeTrendingRow(row) {
  return {
    symbol: row.ticker || row.symbol || row.nse_code || row.company || '—',
    name: row.company || row.name || row.ticker || '—',
    price: row.current_price ?? row.price ?? row.ltp ?? null,
    change: row.percent_change ?? row.percentChange ?? row.change ?? null,
  };
}

export async function getTickerData(env = {}) {
  return oncePerMarketCycle('market-ticker', () => fetchTickerData(env));
}

async function fetchTickerData(env = {}) {
  const now = Date.now();
  const apiKey = env.indianApiKey || '';
  const baseUrl = env.indianApiBase || 'https://stock.indianapi.in';

  let rows = [];
  const growwAllowed = isGrowwConfigured() && now >= growwBackoffUntil;

  if (growwAllowed) {
    try {
      rows = (await fetchGrowwTicker()).filter((row) => {
        const price = Number(row?.price);
        return Number.isFinite(price) && price > 0;
      });
    } catch (err) {
      const msg = String(err?.message || err);
      console.warn('[marketData] Groww ticker failed:', msg);
      if (/rate limit|too many|429/i.test(msg)) {
        growwBackoffUntil = Date.now() + 5 * 60_000;
      }
    }
  }

  // Always merge NSE so mid/small-cap and any missing cash indices are available.
  // Groww remains preferred when both return the same name.
  const nseRows = await fetchNseIndices().catch(() => []);
  if (nseRows.length) {
    const prefer = new Map();
    for (const row of rows) {
      const key = String(row?.name || '').trim().toUpperCase();
      if (key) prefer.set(key, row);
    }
    for (const row of nseRows) {
      const key = String(row?.name || '').trim().toUpperCase();
      if (key && !prefer.has(key)) prefer.set(key, row);
    }
    rows = [...prefer.values()];
  }

  const commodities = await fetchCommodities(apiKey, baseUrl).catch(() => []);

  const extraCommodities = [
    { id: 'usd-inr', name: 'USD/INR', price: null, change: null, percentChange: null, source: 'pending' },
    { id: 'gold', name: 'GOLD', price: null, change: null, percentChange: null, source: 'pending' },
    { id: 'silver', name: 'SILVER', price: null, change: null, percentChange: null, source: 'pending' },
    { id: 'brent', name: 'BRENT', price: null, change: null, percentChange: null, source: 'pending' },
    { id: 'gift-nifty', name: 'GIFT NIFTY', price: null, change: null, percentChange: null, source: 'pending' },
  ];

  for (const extra of extraCommodities) {
    const match = commodities.find(
      (c) => String(c.name).toUpperCase().includes(extra.name.split('/')[0])
    );
    if (match) rows.push(match);
    else rows.push(extra);
  }

  return {
    items: rows,
    source: isGrowwConfigured() ? 'groww+fallback' : 'fallback',
    updatedAt: new Date().toISOString(),
  };
}

export async function getDashboardData(env = {}) {
  return oncePerMarketCycle('market-dashboard', () => fetchDashboardData(env));
}

async function fetchDashboardData(env = {}) {
  const apiKey = env.indianApiKey || '';
  const baseUrl = env.indianApiBase || 'https://stock.indianapi.in';

  const [ticker, trending] = await Promise.all([
    getTickerData(env),
    fetchTrending(apiKey, baseUrl),
  ]);

  const items = ticker.items || [];
  const nifty50 = findIndex(items, 'NIFTY 50', 'NIFTY');
  const bankNifty = findIndex(items, 'BANK NIFTY', 'NIFTY BANK');
  const vix = findIndex(items, 'INDIA VIX');
  const usdInr = findIndex(items, 'USD/INR');
  const gold = findIndex(items, 'GOLD');
  const brent = findIndex(items, 'BRENT');

  const gainers = (trending.gainers || []).map(normalizeTrendingRow);
  const losers = (trending.losers || []).map(normalizeTrendingRow);

  const outlookInputs = {
    indices: {
      nifty50: { percentChange: nifty50?.percentChange ?? nifty50?.change },
      bankNifty: { percentChange: bankNifty?.percentChange ?? bankNifty?.change },
      vix: { price: vix?.price, percentChange: vix?.percentChange },
    },
    breadth: {
      gainers: gainers.length,
      losers: losers.length,
    },
    commodities: {
      usdInr: { percentChange: usdInr?.percentChange },
      brent: { percentChange: brent?.percentChange },
      gold: { percentChange: gold?.percentChange },
    },
    sectors: { top: { name: 'Capital Goods' } },
  };

  const outlook = computeMarketOutlook(outlookInputs);
  const pulse = computeMarketPulse(outlook, outlookInputs);

  const result = {
    pulse,
    outlook,
    gainers,
    losers,
    breadth: {
      gainers: gainers.length,
      losers: losers.length,
      label: outlook.marketBreadth,
    },
    stocksInFocus: gainers.slice(0, 3).map((g) => g.symbol),
    upcomingResults: [],
    upcomingIpos: [],
    fiiDii: null,
    updatedAt: new Date().toISOString(),
  };

  return result;
}
