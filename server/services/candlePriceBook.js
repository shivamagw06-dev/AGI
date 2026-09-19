import { getHistoricalCandles } from '../providers/upstox.js';
import { istDateKey } from './liveAlphaSession.js';

/**
 * Settlement prices from Upstox one-minute history.
 *
 * Outcome tracking needs the price at a past instant: five minutes after a
 * signal, at the close, five sessions later. Live snapshots only exist while
 * the feed is up and are pruned after 25 days, so a feed outage or a restart
 * left outcomes with nothing to settle against. The public history endpoint
 * has every minute of every session, needs no token, and is only published
 * once a session has ended, so this book prices dates before today (IST).
 *
 * The price at an instant is the close of the last one-minute candle that had
 * finished by then: the 09:24 candle settles 09:25. An instant after 15:30
 * takes the session's last candle, and one before 09:16 has no price.
 */

const MINUTE_MS = 60_000;
const IST_OFFSET_MS = 5.5 * 60 * 60_000;

/**
 * Upstox has no instrument under three sector keys Live Alpha used before
 * 20 Sep 2026. Rows anchored under them (via the Groww fallback) are priced
 * from the index the fallback actually quoted.
 */
export const CANDLE_KEY_ALIASES = Object.freeze({
  'NSE_INDEX|Nifty Financial Services': 'NSE_INDEX|Nifty Fin Service',
  'NSE_INDEX|Nifty Infrastructure': 'NSE_INDEX|Nifty Infra',
  'NSE_INDEX|Nifty India Digital': 'NSE_INDEX|Nifty IT',
});

export function candleKey(instrumentKey) {
  const key = String(instrumentKey || '').trim();
  return CANDLE_KEY_ALIASES[key] || key;
}

/** Candle rows as [endMs, close], oldest first. */
export function parseMinuteCandles(payload) {
  const candles = payload?.data?.candles;
  if (!Array.isArray(candles)) return [];
  return candles
    .map((row) => [Date.parse(row?.[0]) + MINUTE_MS, Number(row?.[4])])
    .filter(([end, close]) => Number.isFinite(end) && Number.isFinite(close) && close > 0)
    .sort((a, b) => a[0] - b[0]);
}

/** One session's candles as two typed arrays: about 6 KB, not 20 KB of pairs. */
export function packCandles(rows) {
  return { ends: Float64Array.from(rows, (row) => row[0]), closes: Float64Array.from(rows, (row) => row[1]) };
}

export function priceFromCandles({ ends, closes }, atMs) {
  let found = -1;
  for (let index = 0; index < ends.length && ends[index] <= atMs; index += 1) found = index;
  return found < 0 ? null : { price: closes[found], candle_end: new Date(ends[found]).toISOString() };
}

export function todayIst(now = Date.now()) {
  return new Date(now + IST_OFFSET_MS).toISOString().slice(0, 10);
}

export class CandlePriceBook {
  constructor({
    fetchCandles = (key, date) => getHistoricalCandles(key, { unit: 'minutes', interval: 1, from: date, to: date }),
    requestsPerSecond = Number(process.env.LIVE_ALPHA_OUTCOME_CANDLE_RPS || 0.5),
    maxEntries = 3000,
    sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    clock = () => Date.now(),
  } = {}) {
    this.fetchCandles = fetchCandles;
    // The account's history quota is shared with the other candle jobs; the
    // default of one request every two seconds uses under half of it.
    this.minGapMs = 1000 / Math.max(0.01, Number(requestsPerSecond) || 0.5);
    this.maxEntries = maxEntries;
    this.sleep = sleep;
    this.clock = clock;
    this.cache = new Map();
    this.lastRequestMs = 0;
    this.queue = Promise.resolve();
    this.stats = { requests: 0, cache_hits: 0, errors: 0, empty: 0 };
  }

  /**
   * Wait for this request's turn. Several jobs share one book, so the spacing
   * is a queue: two callers never read the same last-request time and fire
   * together.
   */
  #slot() {
    const turn = this.queue.then(async () => {
      const wait = this.lastRequestMs + this.minGapMs - this.clock();
      if (wait > 0) await this.sleep(wait);
      this.lastRequestMs = this.clock();
    });
    this.queue = turn.catch(() => {});
    return turn;
  }

  async #rows(key, date) {
    const cacheKey = `${key}|${date}`;
    if (this.cache.has(cacheKey)) {
      const rows = this.cache.get(cacheKey);
      this.cache.delete(cacheKey);
      this.cache.set(cacheKey, rows);
      this.stats.cache_hits += 1;
      return rows;
    }
    await this.#slot();
    this.stats.requests += 1;
    let rows;
    try {
      rows = packCandles(parseMinuteCandles(await this.fetchCandles(key, date)));
    } catch (error) {
      this.stats.errors += 1;
      // A refusal of this key (an expired contract, a retired ISIN) is about
      // the key, not the service: remember it and let the caller move on.
      // Throttling, server errors and network failures still propagate.
      const status = Number(error?.status);
      if (!(status >= 400 && status < 500 && status !== 429)) throw error;
      rows = { ends: new Float64Array(0), closes: new Float64Array(0), refused: /invalid instrument/i.test(error.message) ? 'invalid_instrument_key' : `upstox_${status}` };
    }
    if (!rows.ends.length && !rows.refused) this.stats.empty += 1;
    this.cache.set(cacheKey, rows);
    while (this.cache.size > this.maxEntries) this.cache.delete(this.cache.keys().next().value);
    return rows;
  }

  /**
   * Price of `instrumentKey` at `at`, or a reason it has none.
   * Returns { price, candle_end } or { price: null, reason }.
   */
  async priceAt(instrumentKey, at) {
    const atMs = new Date(at).getTime();
    if (!Number.isFinite(atMs)) return { price: null, reason: 'invalid_time' };
    const date = istDateKey(atMs);
    if (date >= todayIst(this.clock())) return { price: null, reason: 'session_not_published' };
    const rows = await this.#rows(candleKey(instrumentKey), date);
    if (rows.refused) return { price: null, reason: rows.refused };
    if (!rows.ends.length) return { price: null, reason: 'no_candles' };
    return priceFromCandles(rows, atMs) || { price: null, reason: 'before_first_candle' };
  }
}

let shared = null;

/**
 * The one book the settlement jobs share, so together they stay inside the
 * request rate and reuse each other's candles.
 */
export function sharedCandleBook() {
  shared ||= new CandlePriceBook();
  return shared;
}
