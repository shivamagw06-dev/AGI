/**
 * Turning a Yahoo chart payload into daily bars we can trust.
 *
 * Two properties of that payload decide whether a backtest built on it is
 * honest, and both are easy to get wrong.
 *
 * The first is which price to use. Yahoo's `close` is retroactively adjusted
 * for splits: Apple's 2020-08-28 close comes back as 124.81, not the 499.23 it
 * actually traded at, because of the 4-for-1 that August. A position value
 * reconstructed from a 13F share count and that price is wrong by the split
 * factor. Returns, on the other hand, need `adjclose`, which is adjusted for
 * dividends as well. Both are kept and named for what they are, so a caller
 * cannot reach for the wrong one by accident.
 *
 * The second is the date. Timestamps arrive as seconds and the bar belongs to
 * the session's own calendar day in the exchange's timezone. Reading them in
 * UTC works for US equities by luck - the open is 13:30 or 14:30 UTC, safely
 * mid-day - and stops working for any exchange that trades across the UTC
 * midnight. The timezone is in the payload, so it is used rather than assumed.
 */

/**
 * A price, or null if there wasn't one.
 *
 * Null and undefined are absences, not zeros; a non-positive number is not a
 * price a share traded at and is treated as an absence too.
 */
function toPrice(value) {
  if (value === null || value === undefined) return null;
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? num : null;
}

/** The session date of a timestamp, in the exchange's own timezone. */
export function sessionDate(epochSeconds, timeZone = 'America/New_York') {
  const seconds = Number(epochSeconds);
  if (!Number.isFinite(seconds)) return null;
  try {
    // en-CA renders as YYYY-MM-DD, which is the shape we store.
    return new Intl.DateTimeFormat('en-CA', {
      timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(new Date(seconds * 1000));
  } catch {
    return null;
  }
}

/**
 * Extract daily bars from a Yahoo chart result.
 *
 * A session with no close is dropped rather than carried forward. Yahoo emits
 * nulls for halts and for days an exchange was shut, and a null that becomes
 * the previous day's price is a fabricated observation - it would show a stock
 * trading flat through a suspension it never traded in.
 */
export function barsFromChart(result, { ticker = null } = {}) {
  const timestamps = result?.timestamp;
  if (!Array.isArray(timestamps) || !timestamps.length) return [];

  const quote = result?.indicators?.quote?.[0] || {};
  const adjcloses = result?.indicators?.adjclose?.[0]?.adjclose;
  const timeZone = result?.meta?.exchangeTimezoneName || 'America/New_York';
  const currency = result?.meta?.currency || null;

  const bars = [];
  const seen = new Set();
  for (let i = 0; i < timestamps.length; i += 1) {
    // Number(null) is 0, and 0 is finite. Coercing first would turn a halted
    // session into a price of zero - a position worth nothing and a -100%
    // return - so the absence is checked before the value is read.
    const close = toPrice(quote.close?.[i]);
    if (close === null) continue;

    const date = sessionDate(timestamps[i], timeZone);
    if (!date) continue;
    // A repeated session date means the payload carried an intraday bar or a
    // duplicate; the first is kept rather than letting the last silently win.
    if (seen.has(date)) continue;
    seen.add(date);

    bars.push({
      ticker,
      price_date: date,
      // Split-adjusted, as Yahoo returns it. Not the traded price on the day.
      close,
      // Split and dividend adjusted. This is what a return is computed from.
      adjusted_close: toPrice(adjcloses?.[i]),
      currency,
    });
  }
  return bars;
}

/**
 * Whether a symbol's history looks like it stopped.
 *
 * A delisted or renamed ticker keeps returning its old history, so a caller
 * that only checks for an empty response will treat a dead symbol as healthy
 * and quietly value a position at a price from years ago. Comparing the last
 * bar against the run date makes that visible instead.
 */
export function listingStatus(bars, asOf, staleAfterDays = 15) {
  if (!bars?.length) return 'unknown';
  const last = bars[bars.length - 1]?.price_date;
  if (!last || !asOf) return 'unknown';
  const days = (Date.parse(asOf) - Date.parse(last)) / 86_400_000;
  if (!Number.isFinite(days)) return 'unknown';
  return days > staleAfterDays ? 'stale_or_delisted' : 'active';
}
