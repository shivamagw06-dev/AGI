/**
 * Quotes for the India AI enablers basket, from the Upstox V3 feed.
 *
 * This is an adapter, not a feed. `UpstoxMarketFeedV3` already owns the
 * socket, the protobuf and the reconnect, and `SynchronizedSnapshotStore`
 * already rejects out-of-order and future-dated ticks. What is missing between
 * that store and `aiEnablersIndex` is four things, and each of them is a place
 * where a number can quietly stop meaning what it says:
 *
 *   - the mapping from a universe member to an instrument key, which must be
 *     resolved rather than assumed;
 *   - a shape change, from the store's snapshot row to the {ltp,
 *     previousClose, at} the index reads;
 *   - a last-good price for the gap between ticks, which must never become a
 *     permanent substitute for a price;
 *   - a volume ratio that is not misleading before the close.
 */

/** NSE continuous session, in IST minutes from midnight. */
const SESSION_OPEN_MIN = 9 * 60 + 15;
const SESSION_CLOSE_MIN = 15 * 60 + 30;
const SESSION_MINUTES = SESSION_CLOSE_MIN - SESSION_OPEN_MIN;
const IST_OFFSET_MIN = 5 * 60 + 30;

/**
 * How long a last-good price may stand in for a live one.
 *
 * Deliberately short, and deliberately not the same as the index's staleness
 * window. A last-good price exists to cover the seconds between ticks in an
 * illiquid name, not to keep a dead feed looking alive. Past this age the
 * quote is dropped entirely, coverage falls, and the index refuses - which is
 * the behaviour we actually want when the feed dies.
 */
export const LAST_GOOD_MAX_AGE_MS = 300_000;

/** A member's instrument key, or the reason it has none. */
export function instrumentKeyFor(member) {
  const explicit = String(member?.instrumentKey || '').trim();
  if (explicit) {
    if (!explicit.includes('|')) return { key: null, reason: 'MALFORMED_INSTRUMENT_KEY' };
    return { key: explicit, reason: null };
  }
  const isin = String(member?.isin || '').trim().toUpperCase();
  if (!/^IN[A-Z0-9]{10}$/.test(isin)) return { key: null, reason: 'NO_ISIN' };
  return { key: `NSE_EQ|${isin}`, reason: null };
}

/**
 * Every instrument the basket needs, including the benchmark.
 *
 * Returns the unresolved members too. A member we cannot key is not a member
 * we can price, and it has to be visible rather than silently absent from a
 * subscription list.
 */
export function universeInstrumentKeys(universe) {
  const members = (universe?.members || []).filter((one) => one.admitted !== false);
  const bySymbol = new Map();
  const unresolved = [];
  for (const member of members) {
    const { key, reason } = instrumentKeyFor(member);
    if (!key) {
      unresolved.push({ symbol: member.symbol, reason });
      continue;
    }
    bySymbol.set(member.symbol, key);
  }
  const benchmarkKey = String(universe?.benchmarkKey || '').trim() || null;
  const keys = [...new Set([...bySymbol.values(), ...(benchmarkKey ? [benchmarkKey] : [])])];
  return { bySymbol, benchmarkKey, keys, unresolved };
}

/**
 * The last price we accepted for each instrument, and when.
 *
 * Separate from the snapshot store because the store holds the latest tick
 * whatever its age, and this holds the latest tick we were willing to *use*.
 * The distinction matters when the feed reconnects: the store may still carry
 * a pre-disconnect row, and serving it as though it were current is exactly
 * the failure this class exists to make visible.
 */
export class LastGoodPrices {
  constructor({ maxAgeMs = LAST_GOOD_MAX_AGE_MS } = {}) {
    this.maxAgeMs = maxAgeMs;
    this.prices = new Map();
  }

  remember(instrumentKey, { ltp, previousClose, at, cumulativeVolume = null }) {
    if (!Number.isFinite(ltp) || !Number.isFinite(previousClose) || !Number.isFinite(at)) return;
    const previous = this.prices.get(instrumentKey);
    if (previous && previous.at > at) return;   // never move a last-good backwards
    this.prices.set(instrumentKey, { ltp, previousClose, at, cumulativeVolume });
  }

  get(instrumentKey, { now }) {
    const row = this.prices.get(instrumentKey);
    if (!row) return null;
    if (now - row.at > this.maxAgeMs) return null;
    return row;
  }

  size() {
    return this.prices.size;
  }
}

const numeric = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/**
 * One instrument's quote, from the store if it is fresh, from last-good if it
 * is not, and absent if neither can be trusted.
 *
 * `source` is always reported. A caller that treats a last-good quote as live
 * is making a choice; it should have to make it knowingly.
 */
export function quoteFor(instrumentKey, { store, lastGood, now, staleMs }) {
  const row = store?.get?.(instrumentKey) || null;
  if (row) {
    const at = Date.parse(row.effective_timestamp || row.received_at || '');
    const ltp = numeric(row.ltp);
    const previousClose = numeric(row.previous_close);
    if (Number.isFinite(at) && ltp !== null && previousClose !== null && previousClose !== 0) {
      lastGood?.remember(instrumentKey, {
        ltp, previousClose, at, cumulativeVolume: numeric(row.cumulative_volume),
      });
      if (now - at <= staleMs) {
        return {
          ltp, previousClose, at, source: 'live', ageMs: Math.max(0, now - at),
          cumulativeVolume: numeric(row.cumulative_volume),
        };
      }
    }
  }
  const fallback = lastGood?.get(instrumentKey, { now });
  if (fallback) {
    return {
      ltp: fallback.ltp, previousClose: fallback.previousClose, at: fallback.at,
      source: 'last_good', ageMs: Math.max(0, now - fallback.at),
      cumulativeVolume: fallback.cumulativeVolume,
    };
  }
  return null;
}

/**
 * The quote book the index reads, keyed by symbol.
 *
 * The returned `quotes` object is exactly the shape `aiEnablersIndex.priced`
 * expects. Everything else in the return value is about how much of it is
 * real, which the page has to show and the index has to be able to refuse on.
 */
export function quoteBook(universe, { store, lastGood, now = Date.now(), staleMs = 60_000 } = {}) {
  const { bySymbol, benchmarkKey, unresolved } = universeInstrumentKeys(universe);
  const quotes = {};
  const sources = { live: [], last_good: [], missing: [] };
  for (const [symbol, key] of bySymbol) {
    const quote = quoteFor(key, { store, lastGood, now, staleMs });
    if (!quote) {
      sources.missing.push(symbol);
      continue;
    }
    // `source` travels with the quote: the index needs it to know that this
    // one's age has already been adjudicated here.
    quotes[symbol] = {
      ltp: quote.ltp, previousClose: quote.previousClose, at: quote.at, source: quote.source,
    };
    sources[quote.source].push(symbol);
  }
  const benchmark = benchmarkKey
    ? quoteFor(benchmarkKey, { store, lastGood, now, staleMs })
    : null;
  return {
    quotes,
    benchmark,
    benchmarkKey,
    sources,
    unresolved,
    asOf: now,
  };
}

/**
 * How much of the session has elapsed, as a fraction.
 *
 * Needed because cumulative volume is a partial-day figure. Comparing it to a
 * full-day average makes every stock look quiet at 10am and normal at 3pm,
 * which is an artefact of the clock rather than anything about the stock.
 */
export function sessionElapsedFraction(now, { openMin = SESSION_OPEN_MIN, closeMin = SESSION_CLOSE_MIN } = {}) {
  const ist = new Date(now + IST_OFFSET_MIN * 60_000);
  const minutes = ist.getUTCHours() * 60 + ist.getUTCMinutes() + ist.getUTCSeconds() / 60;
  if (minutes <= openMin) return 0;
  if (minutes >= closeMin) return 1;
  return (minutes - openMin) / (closeMin - openMin);
}

/**
 * Today's volume against a normal day's, adjusted for the time of day.
 *
 * Returns null rather than a number whenever the comparison would not mean
 * anything: before the open, with no baseline, or in the first minutes when
 * the elapsed fraction is small enough that the ratio is mostly noise.
 */
export function volumeRatio({ cumulativeVolume, averageDailyVolume, now, minimumElapsed = 0.02 }) {
  const volume = numeric(cumulativeVolume);
  const baseline = numeric(averageDailyVolume);
  if (volume === null || baseline === null || baseline <= 0) {
    return { ratio: null, reason: 'NO_BASELINE', elapsed: null };
  }
  const elapsed = sessionElapsedFraction(now);
  if (elapsed <= minimumElapsed) {
    return { ratio: null, reason: 'SESSION_TOO_YOUNG', elapsed };
  }
  return { ratio: Number((volume / (baseline * elapsed)).toFixed(4)), reason: null, elapsed: Number(elapsed.toFixed(4)) };
}

export const SESSION = Object.freeze({ SESSION_OPEN_MIN, SESSION_CLOSE_MIN, SESSION_MINUTES, IST_OFFSET_MIN });
