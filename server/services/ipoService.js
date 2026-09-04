const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;
const CACHE_TTL_MS = 5 * 60 * 1000;
const UPCOMING_LIMIT = 6;
const ACTIVE_LIMIT = 6;
const UPSTOX_BASE = (process.env.UPSTOX_API_BASE || 'https://api.upstox.com/v2').replace(/\/$/, '');

let cache = null;
let cacheAt = 0;
let refreshTimer = null;
let inflight = null;
const detailCache = new Map();

function upstoxToken() {
  return String(
    process.env.UPSTOX_ACCESS_TOKEN ||
    process.env.UPSTOX_TOKEN ||
    process.env.UPSTOX_API_TOKEN ||
    ''
  ).trim();
}

function nextNoonIstMs() {
  const now = new Date();
  const ist = new Date(now.getTime() + IST_OFFSET_MS);
  let targetUtc = Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate(), 6, 30, 0);
  if (targetUtc <= now.getTime()) targetUtc += 24 * 60 * 60 * 1000;
  return targetUtc;
}

async function fetchJson(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const text = await response.text();
    let payload = null;
    try { payload = text ? JSON.parse(text) : null; } catch { payload = null; }
    if (!response.ok) {
      const message = payload?.errors?.[0]?.message || payload?.message || text || `Request failed (${response.status})`;
      throw new Error(message);
    }
    return payload;
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeUpstox(item = {}) {
  const timeline = item.timeline || {};
  return {
    ipoId: item.id || null,
    symbol: item.symbol || null,
    name: item.name || 'IPO',
    status: item.status || null,
    isin: item.isin || null,
    issueType: item.issue_type || null,
    isSme: item.issue_type === 'sme',
    issueSize: item.issue_size ?? null,
    industry: item.industry || null,
    detail: item.additional_text || null,
    minPrice: item.minimum_price ?? null,
    maxPrice: item.maximum_price ?? null,
    cutOffPrice: item.cut_off_price ?? null,
    biddingStartDate: item.bidding_start_date || timeline.application_start_date || null,
    biddingEndDate: item.bidding_end_date || timeline.application_end_date || null,
    dailyStartTime: item.daily_start_time || null,
    dailyEndTime: item.daily_end_time || null,
    faceValue: item.face_value ?? null,
    tickSize: item.tick_size ?? null,
    lotSize: item.lot_size ?? null,
    minimumBidQuantity: item.minimum_quantity ?? null,
    subscriptionRate: item.total_subscription ?? null,
    listingPrice: item.listing_price ?? null,
    listingExchange: item.listing_exchange || null,
    listingDate: timeline.listing_date || item.listing_date || null,
    allotmentDate: timeline.allotment_date || item.allotment_date || null,
    refundInitiationDate: timeline.refund_initiation_date || null,
    preApplyStartDate: timeline.pre_apply_start_date || null,
    mandateEndDate: timeline.mandate_end_date || null,
    rhpUrl: item.rhp_url || null,
    drhpUrl: item.drhp_url || null,
    documentUrl: item.rhp_url || item.drhp_url || null,
    registrarInfo: item.registrar_info || null,
    timeline,
  };
}

function normalizeIndianApi(item = {}) {
  return {
    ipoId: null,
    symbol: item.symbol || null,
    name: item.name || 'IPO',
    status: item.status || null,
    isin: item.isin || null,
    issueType: item.is_sme ? 'sme' : 'regular',
    isSme: Boolean(item.is_sme),
    issueSize: item.issue_size ?? null,
    industry: item.industry || null,
    detail: item.additional_text || null,
    minPrice: item.min_price ?? null,
    maxPrice: item.max_price ?? null,
    cutOffPrice: item.cut_off_price ?? null,
    biddingStartDate: item.bidding_start_date || null,
    biddingEndDate: item.bidding_end_date || null,
    listingDate: item.listing_date || null,
    allotmentDate: item.allotment_date || null,
    lotSize: item.lot_size ?? null,
    minimumBidQuantity: item.min_bid_quantity ?? null,
    subscriptionRate: item.total_subscription_rate ?? null,
    listingPrice: item.listing_price ?? null,
    listingExchange: item.listing_exchange || null,
    rhpUrl: item.rhp_url || item.document_url || null,
    drhpUrl: item.drhp_url || null,
    documentUrl: item.document_url || item.rhp_url || item.drhp_url || null,
    timeline: {},
    registrarInfo: null,
  };
}

function emptySnapshot(unavailable = false) {
  return {
    active: [], upcoming: [], closed: [], listed: [],
    source: 'IPO data unavailable',
    updatedAt: new Date().toISOString(),
    nextRefreshAt: new Date(Date.now() + CACHE_TTL_MS).toISOString(),
    unavailable,
  };
}

function scheduleNoonRefresh() {
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    await refreshIpoSnapshot(true);
    scheduleNoonRefresh();
  }, Math.max(1000, nextNoonIstMs() - Date.now()));
  refreshTimer.unref?.();
}

async function getUpstoxStatus(status, token) {
  const url = new URL(`${UPSTOX_BASE}/ipos`);
  url.searchParams.set('status', status);
  url.searchParams.set('page_number', '1');
  url.searchParams.set('records', '30');
  const payload = await fetchJson(url, {
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
  });
  return Array.isArray(payload?.data) ? payload.data.map(normalizeUpstox) : [];
}

async function loadUpstoxSnapshot() {
  const token = upstoxToken();
  if (!token) throw new Error('Upstox access token is not configured');
  const [active, upcoming, closed, listed] = await Promise.all([
    getUpstoxStatus('open', token),
    getUpstoxStatus('upcoming', token),
    getUpstoxStatus('closed', token),
    getUpstoxStatus('listed', token),
  ]);
  return {
    active, upcoming, closed, listed,
    source: 'Upstox IPO API',
    updatedAt: new Date().toISOString(),
    nextRefreshAt: new Date(Date.now() + CACHE_TTL_MS).toISOString(),
    unavailable: false,
  };
}

async function loadIndianApiSnapshot() {
  const apiKey = String(process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || '').trim();
  const baseUrl = String(process.env.INDIANAPI_BASE || 'https://stock.indianapi.in').replace(/\/$/, '');
  if (!apiKey) throw new Error('IndianAPI key is not configured');
  const payload = await fetchJson(`${baseUrl}/ipo`, {
    headers: { Accept: 'application/json', 'x-api-key': apiKey },
  });
  return {
    active: (payload?.active || []).map(normalizeIndianApi),
    upcoming: (payload?.upcoming || []).map(normalizeIndianApi),
    closed: (payload?.closed || []).map(normalizeIndianApi),
    listed: (payload?.listed || []).map(normalizeIndianApi),
    source: 'IndianAPI IPO data (fallback)',
    updatedAt: new Date().toISOString(),
    nextRefreshAt: new Date(Date.now() + CACHE_TTL_MS).toISOString(),
    unavailable: false,
  };
}

async function refreshIpoSnapshot(force = false) {
  if (!force && cache && Date.now() - cacheAt < CACHE_TTL_MS) return cache;
  if (inflight) return inflight;
  inflight = (async () => {
    try {
      cache = await loadUpstoxSnapshot();
      cacheAt = Date.now();
      return cache;
    } catch (upstoxError) {
      console.warn('[ipo][upstox]', upstoxError.message);
      try {
        cache = await loadIndianApiSnapshot();
        cacheAt = Date.now();
        return cache;
      } catch (fallbackError) {
        console.warn('[ipo][fallback]', fallbackError.message);
        return cache ? { ...cache, unavailable: true } : emptySnapshot(true);
      }
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}

export async function getIpoSnapshot() {
  await refreshIpoSnapshot();
  scheduleNoonRefresh();
  return cache || emptySnapshot(true);
}

function buildCalendar(snapshot) {
  const events = [];
  const push = (ipo, date, label) => {
    if (date) events.push({ date, label, symbol: ipo.symbol, name: ipo.name, status: ipo.status, isSme: ipo.isSme });
  };
  for (const ipo of [...snapshot.upcoming, ...snapshot.active, ...snapshot.closed, ...snapshot.listed]) {
    push(ipo, ipo.preApplyStartDate, 'Pre-apply opens');
    push(ipo, ipo.biddingStartDate, 'IPO opens');
    push(ipo, ipo.biddingEndDate, 'IPO closes');
    push(ipo, ipo.allotmentDate, 'Allotment');
    push(ipo, ipo.refundInitiationDate, 'Refund initiation');
    push(ipo, ipo.listingDate, 'Listing');
  }
  return events.sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

function disclaimer() {
  return 'IPO information is provided for informational purposes only and is not an offer, recommendation, or solicitation. Verify offer documents with the issuer, NSE, BSE, or SEBI.';
}

export async function getIpoSummary() {
  const snapshot = await getIpoSnapshot();
  return {
    active: snapshot.active.slice(0, ACTIVE_LIMIT),
    upcoming: snapshot.upcoming.slice(0, UPCOMING_LIMIT),
    source: snapshot.source,
    updatedAt: snapshot.updatedAt,
    nextRefreshAt: snapshot.nextRefreshAt,
    unavailable: snapshot.unavailable,
    disclaimer: disclaimer(),
  };
}

export async function getIpoPlatform() {
  const snapshot = await getIpoSnapshot();
  return {
    ...snapshot,
    calendar: buildCalendar(snapshot),
    counts: {
      active: snapshot.active.length,
      upcoming: snapshot.upcoming.length,
      closed: snapshot.closed.length,
      listed: snapshot.listed.length,
    },
    disclaimer: disclaimer(),
  };
}

async function loadUpstoxDetail(ipo) {
  const token = upstoxToken();
  if (!token || !ipo?.ipoId) return ipo;
  const hit = detailCache.get(ipo.ipoId);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.value;
  const payload = await fetchJson(`${UPSTOX_BASE}/ipos/${encodeURIComponent(ipo.ipoId)}`, {
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
  });
  const value = { ...ipo, ...normalizeUpstox(payload?.data || {}) };
  detailCache.set(ipo.ipoId, { value, at: Date.now() });
  return value;
}

export async function getIpoDetail(rawSymbol) {
  const symbol = String(rawSymbol || '').trim().toUpperCase().replace(/[^A-Z0-9&-]/g, '');
  const snapshot = await getIpoSnapshot();
  const ipo = ['active', 'upcoming', 'closed', 'listed']
    .flatMap((category) => snapshot[category])
    .find((item) => item.symbol === symbol) || null;
  if (!ipo) return { ipo: null, source: snapshot.source, updatedAt: snapshot.updatedAt, unavailable: snapshot.unavailable };
  let detailed = ipo;
  try { detailed = await loadUpstoxDetail(ipo); } catch (error) { console.warn('[ipo][detail]', error.message); }
  return {
    ipo: detailed,
    source: snapshot.source,
    updatedAt: snapshot.updatedAt,
    nextRefreshAt: snapshot.nextRefreshAt,
    unavailable: snapshot.unavailable,
    disclaimer: disclaimer(),
  };
}
