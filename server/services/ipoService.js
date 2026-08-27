const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;
const UPCOMING_LIMIT = 6;
const ACTIVE_LIMIT = 6;

let cache = null;
let refreshTimer = null;
let inflight = null;

function nextNoonIstMs() {
  const now = new Date();
  const ist = new Date(now.getTime() + IST_OFFSET_MS);
  let targetUtc = Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate(), 6, 30, 0);
  if (targetUtc <= now.getTime()) targetUtc += 24 * 60 * 60 * 1000;
  return targetUtc;
}

function publicIpo(item = {}) {
  return {
    symbol: item.symbol || null,
    name: item.name || 'IPO',
    status: item.status || null,
    isSme: Boolean(item.is_sme),
    detail: item.additional_text || null,
    minPrice: item.min_price ?? null,
    maxPrice: item.max_price ?? null,
    biddingStartDate: item.bidding_start_date || null,
    biddingEndDate: item.bidding_end_date || null,
    listingDate: item.listing_date || null,
    allotmentDate: item.allotment_date || null,
    lotSize: item.lot_size ?? null,
    minimumBidQuantity: item.min_bid_quantity ?? null,
    subscriptionRate: item.total_subscription_rate ?? null,
    documentUrl: item.document_url || null,
  };
}

function emptySnapshot(unavailable = false) {
  return {
    active: [],
    upcoming: [],
    closed: [],
    listed: [],
    source: 'IndianAPI IPO data',
    updatedAt: new Date().toISOString(),
    nextRefreshAt: new Date(nextNoonIstMs()).toISOString(),
    unavailable,
  };
}

function scheduleNoonRefresh() {
  if (refreshTimer) clearTimeout(refreshTimer);
  const delay = Math.max(1_000, nextNoonIstMs() - Date.now());
  refreshTimer = setTimeout(async () => {
    await refreshIpoSnapshot();
    scheduleNoonRefresh();
  }, delay);
  refreshTimer.unref?.();
}

async function refreshIpoSnapshot() {
  if (inflight) return inflight;
  inflight = (async () => {
    try {
      const apiKey = (process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || '').trim();
      const baseUrl = (process.env.INDIANAPI_BASE || 'https://stock.indianapi.in').replace(/\/$/, '');
      if (!apiKey) throw new Error('IndianAPI key is not configured');
      const response = await fetch(`${baseUrl}/ipo`, {
        headers: { Accept: 'application/json', 'x-api-key': apiKey },
      });
      if (!response.ok) throw new Error(`IndianAPI IPO request failed (${response.status})`);
      const payload = await response.json();
      cache = {
        active: (payload.active || []).map(publicIpo),
        upcoming: (payload.upcoming || []).map(publicIpo),
        closed: (payload.closed || []).map(publicIpo),
        listed: (payload.listed || []).map(publicIpo),
        source: 'IndianAPI IPO data',
        updatedAt: new Date().toISOString(),
        nextRefreshAt: new Date(nextNoonIstMs()).toISOString(),
        unavailable: false,
      };
      return cache;
    } catch (error) {
      console.warn('[ipo]', error.message);
      return cache ? { ...cache, unavailable: true } : emptySnapshot(true);
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}

export async function getIpoSnapshot() {
  if (!cache) await refreshIpoSnapshot();
  scheduleNoonRefresh();
  return cache || emptySnapshot(true);
}

function buildCalendar(snapshot) {
  const events = [];
  const push = (ipo, date, label) => {
    if (!date) return;
    events.push({
      date,
      label,
      symbol: ipo.symbol,
      name: ipo.name,
      status: ipo.status,
      isSme: ipo.isSme,
    });
  };
  for (const ipo of [...snapshot.upcoming, ...snapshot.active, ...snapshot.closed, ...snapshot.listed]) {
    push(ipo, ipo.biddingStartDate, 'IPO Opens');
    push(ipo, ipo.biddingEndDate, 'IPO Closes');
    push(ipo, ipo.allotmentDate, 'Allotment');
    push(ipo, ipo.listingDate, 'Listing');
  }
  return events.sort((a, b) => String(a.date).localeCompare(String(b.date)));
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
    disclaimer: 'IPO information is provided for informational purposes only and is not an offer, recommendation, or solicitation. Verify offer documents with the issuer, NSE, BSE, or SEBI.',
  };
}

/** Full IPO Intelligence Platform payload (soft-wire over IndianAPI snapshot). */
export async function getIpoPlatform() {
  const snapshot = await getIpoSnapshot();
  return {
    active: snapshot.active,
    upcoming: snapshot.upcoming,
    closed: snapshot.closed,
    listed: snapshot.listed,
    calendar: buildCalendar(snapshot),
    counts: {
      active: snapshot.active.length,
      upcoming: snapshot.upcoming.length,
      closed: snapshot.closed.length,
      listed: snapshot.listed.length,
    },
    source: snapshot.source,
    updatedAt: snapshot.updatedAt,
    nextRefreshAt: snapshot.nextRefreshAt,
    unavailable: snapshot.unavailable,
    disclaimer: 'IPO information is provided for informational purposes only and is not an offer, recommendation, or solicitation. Verify offer documents with the issuer, NSE, BSE, or SEBI.',
  };
}

export async function getIpoDetail(rawSymbol) {
  const symbol = String(rawSymbol || '').trim().toUpperCase().replace(/[^A-Z0-9&-]/g, '');
  const snapshot = await getIpoSnapshot();
  const categories = ['active', 'upcoming', 'closed', 'listed'];
  const ipo = categories.flatMap((category) => snapshot[category]).find((item) => item.symbol === symbol) || null;
  return { ipo, source: snapshot.source, updatedAt: snapshot.updatedAt, nextRefreshAt: snapshot.nextRefreshAt, unavailable: snapshot.unavailable };
}
