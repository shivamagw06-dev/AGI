/**
 * Stamp the newest traded LTP onto a stored Hedge Fund terminal payload.
 *
 * The research ranks stay on the snapshot. Price, CMP and consensus upside
 * track the Live Alpha tape (in-process) and live_market_snapshots (Supabase).
 */

const PRICE_CACHE_MS = 20_000;
const ALIAS_CACHE_MS = 10 * 60_000;
const MAX_AGE_MS = 20 * 60_000;

let priceCache = { at: 0, prices: new Map() };
let aliasCache = { at: 0, rows: [] };

function credentials() {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  return url && key ? { url, key } : null;
}

async function rest(path, timeoutMs = 4_000) {
  const auth = credentials();
  if (!auth) return null;
  const response = await fetch(`${auth.url}/rest/v1/${path}`, {
    method: 'GET',
    headers: {
      apikey: auth.key,
      Authorization: `Bearer ${auth.key}`,
      Accept: 'application/json',
    },
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function putPrice(prices, key, ltp, observedAt, source) {
  const id = String(key || '').trim();
  const px = Number(ltp);
  if (!id || !(px > 0)) return;
  const existing = prices.get(id);
  const nextMs = Date.parse(observedAt || '') || 0;
  const prevMs = Date.parse(existing?.observed_at || '') || 0;
  if (existing && prevMs >= nextMs) return;
  prices.set(id, { ltp: px, observed_at: observedAt || null, source: source || 'live_market_snapshots' });
}

async function loadAliases() {
  const now = Date.now();
  if (now - aliasCache.at < ALIAS_CACHE_MS && aliasCache.rows.length) return aliasCache.rows;
  const query = new URLSearchParams({
    select: 'symbol,instrument_key',
    limit: '4000',
  }).toString();
  const rows = await rest(`company_master?${query}`);
  aliasCache = { at: now, rows: Array.isArray(rows) ? rows : [] };
  return aliasCache.rows;
}

async function loadSnapshotPrices(prices) {
  const since = new Date(Date.now() - MAX_AGE_MS).toISOString();
  const query = new URLSearchParams({
    select: 'instrument_key,observed_at,ltp',
    observed_at: `gte.${since}`,
    order: 'observed_at.desc',
    limit: '5000',
  }).toString();
  const rows = await rest(`live_market_snapshots?${query}`);
  if (!Array.isArray(rows)) return;
  const now = Date.now();
  for (const row of rows) {
    const observed = row?.observed_at;
    const age = now - Date.parse(observed || '');
    if (!Number.isFinite(age) || age > MAX_AGE_MS) continue;
    putPrice(prices, row.instrument_key, row.ltp, observed, 'live_market_snapshots');
  }
  try {
    for (const master of await loadAliases()) {
      const key = String(master?.instrument_key || '').trim();
      const symbol = String(master?.symbol || '').trim().toUpperCase();
      const pack = prices.get(key);
      if (key && symbol && pack) prices.set(symbol, pack);
    }
  } catch {
    /* aliases are optional; instrument_key matches still apply */
  }
}

async function loadPriceMap() {
  const now = Date.now();
  if (now - priceCache.at < PRICE_CACHE_MS && priceCache.prices.size) return priceCache.prices;
  let prices = new Map();
  try {
    const { latestLiveAlphaPrints } = await import('./liveAlphaRuntime.js');
    prices = latestLiveAlphaPrints();
  } catch {
    prices = new Map();
  }
  try {
    await loadSnapshotPrices(prices);
  } catch {
    /* in-process prints are enough for the Live Alpha 500 */
  }
  priceCache = { at: now, prices };
  return prices;
}

function overlayRow(row, prices) {
  const key = String(row.instrument_key || '').trim();
  const symbol = String(row.ticker || row.symbol || '').trim().toUpperCase();
  const pack = (key && prices.get(key)) || (symbol && prices.get(symbol));
  if (!pack) return;
  const priorPrice = Number(row.price ?? row.cmp);
  const priorYield = Number(row.dividend_yield);
  const forwardEps = Number(row.forward_eps ?? row.factors?.forward_eps);
  row.price = pack.ltp;
  row.cmp = pack.ltp;
  row.live_price = pack.ltp;
  row.price_source = pack.source;
  row.price_as_of = pack.observed_at;
  row.data_context = {
    ...(row.data_context || {}),
    price_source: pack.source,
    price_as_of: pack.observed_at,
    price_freshness: 'LIVE',
  };
  const target = Number(row.consensus?.target_price);
  if (row.consensus && target > 0) {
    row.consensus = {
      ...row.consensus,
      upside: Number((((target / pack.ltp) - 1) * 100).toFixed(2)),
    };
    row.consensus_upside = row.consensus.upside;
  }
  if (priorPrice > 0 && Number.isFinite(priorYield) && priorYield >= 0) {
    const dps = (priorYield / 100) * priorPrice;
    row.dividend_yield = Number(((dps / pack.ltp) * 100).toFixed(2));
    if (Number(row.value) === priorYield) row.value = row.dividend_yield;
  }
  if (forwardEps > 0) row.forward_pe = Number((pack.ltp / forwardEps).toFixed(2));
  if (row.market && typeof row.market === 'object') {
    row.market = { ...row.market, price: pack.ltp };
  }
}

function applyInPlace(node, prices) {
  if (Array.isArray(node)) {
    for (const item of node) applyInPlace(item, prices);
    return;
  }
  if (!node || typeof node !== 'object') return;
  for (const value of Object.values(node)) applyInPlace(value, prices);
  if (node.ticker || node.instrument_key || node.symbol) overlayRow(node, prices);
}

export function overlayPayloadWithPrices(payload, priceMap) {
  if (!payload || typeof payload !== 'object') return payload;
  if (!priceMap || priceMap.size === 0) return payload;
  const copy = JSON.parse(JSON.stringify(payload));
  applyInPlace(copy, priceMap);
  return copy;
}

export async function overlayHflLivePrices(payload) {
  if (!payload || typeof payload !== 'object') return payload;
  try {
    return overlayPayloadWithPrices(payload, await loadPriceMap());
  } catch {
    return payload;
  }
}

export function resetHflLivePriceOverlayCache() {
  priceCache = { at: 0, prices: new Map() };
  aliasCache = { at: 0, rows: [] };
}
