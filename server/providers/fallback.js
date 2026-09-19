/**
 * Fallback market data — NSE indices + IndianAPI commodities.
 * Used when Groww is unavailable or for instruments Groww doesn't cover.
 */

const INDEX_NAMES = [
  'NIFTY 50',
  'NIFTY BANK',
  'INDIA VIX',
  'NIFTY MIDCAP 100',
  'NIFTY MIDCAP 50',
  'NIFTY NEXT 50',
  'NIFTY SMALLCAP 100',
  'NIFTY SMALLCAP 50',
];

const NSE_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

async function ensureFetch() {
  if (typeof globalThis.fetch === 'function') return globalThis.fetch.bind(globalThis);
  const mod = await import('node-fetch');
  return mod.default;
}

function collectCookies(resp) {
  const raw =
    typeof resp.headers.getSetCookie === 'function'
      ? resp.headers.getSetCookie()
      : resp.headers.get('set-cookie')
        ? [resp.headers.get('set-cookie')]
        : [];
  return raw
    .map((c) => String(c).split(';')[0].trim())
    .filter(Boolean)
    .join('; ');
}

async function nseSession(fetchFn) {
  try {
    const home = await fetchFn('https://www.nseindia.com/', {
      method: 'GET',
      headers: {
        Accept: 'text/html,application/xhtml+xml',
        'User-Agent': NSE_UA,
      },
      signal: AbortSignal.timeout(10_000),
      redirect: 'follow',
    });
    return collectCookies(home);
  } catch {
    return '';
  }
}

export async function fetchNseIndices() {
  const fetchFn = await ensureFetch();
  const cookie = await nseSession(fetchFn);
  const resp = await fetchFn('https://www.nseindia.com/api/allIndices', {
    headers: {
      Accept: 'application/json',
      'User-Agent': NSE_UA,
      Referer: 'https://www.nseindia.com/',
      ...(cookie ? { Cookie: cookie } : {}),
    },
    signal: AbortSignal.timeout(12_000),
  });
  const text = await resp.text().catch(() => '');
  if (!resp.ok || !text) return [];

  const payload = JSON.parse(text);
  const rows = Array.isArray(payload?.data) ? payload.data : [];
  const wanted = new Set(INDEX_NAMES.map((n) => n.toUpperCase()));

  return rows
    .filter((row) => {
      const name = String(row.index || row.indexSymbol || '').trim().toUpperCase();
      return wanted.has(name);
    })
    .map((row) => ({
      id: String(row.index || row.indexSymbol).toLowerCase().replace(/\s+/g, '-'),
      name: row.index || row.indexSymbol,
      price: row.last ?? row.previousClose ?? null,
      change: row.variation ?? null,
      percentChange: row.percentChange ?? null,
      source: 'nse',
    }));
}

export async function fetchCommodities(apiKey, baseUrl) {
  if (!apiKey) return [];
  const fetchFn = await ensureFetch();
  try {
    const resp = await fetchFn(`${baseUrl}/commodities`, {
      headers: { Accept: 'application/json', 'x-api-key': apiKey },
    });
    const json = await resp.json().catch(() => ({}));
    const items = json?.data || json?.commodities || json || [];
    const list = Array.isArray(items) ? items : [];

    const map = {
      gold: 'GOLD',
      silver: 'SILVER',
      brent: 'BRENT',
      'usd/inr': 'USD/INR',
      usdinr: 'USD/INR',
    };

    return list
      .filter((c) => {
        const key = String(c.name || c.commodity || c.symbol || '').toLowerCase();
        return Object.keys(map).some((k) => key.includes(k));
      })
      .slice(0, 4)
      .map((c) => ({
        id: String(c.name || c.commodity).toLowerCase().replace(/\s+/g, '-'),
        name: map[String(c.name || c.commodity).toLowerCase()] || c.name || c.commodity,
        price: c.price ?? c.last ?? c.value ?? null,
        change: c.change ?? null,
        percentChange: c.percent_change ?? c.percentChange ?? null,
        source: 'indianapi',
      }));
  } catch {
    return [];
  }
}

export async function fetchTrending(apiKey, baseUrl) {
  if (!apiKey) return { gainers: [], losers: [] };
  const fetchFn = await ensureFetch();
  try {
    const resp = await fetchFn(`${baseUrl}/trending`, {
      headers: { Accept: 'application/json', 'x-api-key': apiKey },
    });
    const json = await resp.json().catch(() => ({}));
    const trending = json?.trending_stocks || json?.data?.trending_stocks || json?.data || json || {};
    const gainers = (trending.top_gainers || trending.gainers || []).slice(0, 5);
    const losers = (trending.top_losers || trending.losers || []).slice(0, 5);
    return { gainers, losers, raw: trending };
  } catch {
    return { gainers: [], losers: [] };
  }
}
