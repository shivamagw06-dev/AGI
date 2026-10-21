/**
 * Rebuild the session's minute snapshots from Upstox 1-minute candles.
 *
 * The runtime keeps its snapshot history in memory, so every deploy used to
 * wipe the chart back to a single point. The prices were never lost - Upstox
 * serves the session's 1-minute candles - only our record of them.
 *
 * This replays those candles through exactly the code the live feed goes
 * through: a store row per instrument, `quoteBook` with a fresh last-good
 * memory, `snapshotFrom` and so `computeIndex`. The rebuilt minutes therefore
 * obey the same coverage floor, staleness window, fallback and corporate-
 * action exclusions as the live ones, and refuse in the same places.
 *
 * Two rules keep it honest:
 *
 *   - No look-ahead. A candle stamped 10:04 covers 10:04-10:05 and its close
 *     is not known until 10:05, so it is visible to the 10:05 snapshot and not
 *     before. A snapshot at T sees only candles that had closed by T.
 *   - Marked as rebuilt. Every snapshot carries `origin: 'candles'`, so a
 *     reader can tell a reconstructed minute from one the feed observed.
 */

import { LastGoodPrices, quoteBook, universeInstrumentKeys } from './aiEnablersQuotes.js';
import { snapshotFrom } from './aiEnablersLiveRuntime.js';
import { STALE_MS } from './aiEnablersIndex.js';

const MINUTE_MS = 60_000;
const IST_OFFSET_MS = 330 * 60_000;

/** The IST calendar date of an instant. */
export const istDate = (ms) => new Date(ms + IST_OFFSET_MS).toISOString().slice(0, 10);

const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/**
 * Upstox candle rows, oldest first, with the instant each one closed.
 *
 * Rows are `[timestamp, open, high, low, close, volume, oi]`, newest first.
 * A row we cannot read is dropped rather than guessed at.
 */
export function parseCandles(payload, { minutes = 1 } = {}) {
  const rows = payload?.data?.candles;
  if (!Array.isArray(rows)) return [];
  const out = [];
  for (const row of rows) {
    if (!Array.isArray(row)) continue;
    const start = Date.parse(row[0]);
    const close = numeric(row[4]);
    if (!Number.isFinite(start) || close === null || close <= 0) continue;
    out.push({ start, end: start + minutes * MINUTE_MS, close, volume: numeric(row[5]) ?? 0 });
  }
  return out.sort((a, b) => a.start - b.start);
}

/**
 * The close of the last trading day strictly before the session.
 *
 * "Strictly before" matters: a daily candle for the session itself is that
 * day's running price, and using it as the base would make every return
 * near zero.
 */
export function previousCloseBefore(dailyPayload, sessionDate) {
  const days = parseCandles(dailyPayload, { minutes: 0 })
    .filter((one) => istDate(one.start) < sessionDate);
  if (!days.length) return null;
  const last = days[days.length - 1];
  return { close: last.close, date: istDate(last.start) };
}

/**
 * The session the candles belong to: the IST date of the latest candle.
 *
 * Taken from the data rather than the clock, so a rebuild run on a holiday
 * or before the open cannot pair one day's candles with another day's base.
 */
export function sessionDateOf(candlesByKey) {
  let latest = null;
  for (const candles of Object.values(candlesByKey || {})) {
    const last = candles[candles.length - 1];
    if (last && (latest === null || last.start > latest)) latest = last.start;
  }
  return latest === null ? null : istDate(latest);
}

/**
 * Snapshots for every minute boundary from the first closed candle up to
 * (but not including) `until`.
 *
 * `previousCloseByKey` is the base each return is measured from. An
 * instrument without one is left out of the replay store, and so shows as
 * missing - which lowers coverage and, below the floor, makes the minute
 * refuse. That is the correct outcome: a price without a base is not a
 * return.
 */
export function replaySession(universe, {
  candlesByKey = {},
  previousCloseByKey = {},
  until,
  sessionDate = sessionDateOf(candlesByKey),
  staleMs = STALE_MS,
  coverageFloor,
  volumeBaselines = {},
  priceBreaks = {},
} = {}) {
  if (!sessionDate || !Number.isFinite(until)) return [];
  const { keys } = universeInstrumentKeys(universe);

  // Only the session's own candles, and only instruments with a base.
  const series = new Map();
  for (const key of keys) {
    const base = previousCloseByKey[key];
    const candles = (candlesByKey[key] || []).filter((one) => istDate(one.start) === sessionDate);
    if (!Number.isFinite(base) || base <= 0 || !candles.length) continue;
    series.set(key, { base, candles, next: 0, cumulative: 0, latest: null });
  }
  if (!series.size) return [];

  const firstEnd = Math.min(...[...series.values()].map((one) => one.candles[0].end));
  const lastEnd = Math.max(...[...series.values()].map((one) => one.candles[one.candles.length - 1].end));
  const stop = Math.min(until, lastEnd + MINUTE_MS);

  const rows = new Map();
  const store = { get: (key) => rows.get(key) || null };
  const lastGood = new LastGoodPrices();
  const snapshots = [];

  for (let t = firstEnd; t < stop; t += MINUTE_MS) {
    for (const [key, one] of series) {
      // Advance past every candle that had closed by t, and no further.
      while (one.next < one.candles.length && one.candles[one.next].end <= t) {
        one.latest = one.candles[one.next];
        one.cumulative += one.latest.volume;
        one.next += 1;
      }
      if (!one.latest) continue;
      rows.set(key, {
        ltp: one.latest.close,
        previous_close: one.base,
        effective_timestamp: new Date(one.latest.end).toISOString(),
        cumulative_volume: one.cumulative,
      });
    }
    const book = quoteBook(universe, { store, lastGood, now: t, staleMs, priceBreaks });
    book.volumes = Object.fromEntries(keys.map((key) => [key, rows.get(key)?.cumulative_volume ?? null]));
    const snapshot = snapshotFrom(universe, book, { now: t, staleMs, coverageFloor, volumeBaselines });
    snapshot.origin = 'candles';
    snapshots.push(snapshot);
  }
  return snapshots;
}
