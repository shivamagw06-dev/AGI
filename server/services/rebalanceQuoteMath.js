/**
 * The columns of a rebalance table that move.
 *
 * A published table is a photograph. The flow estimate in it stays true - it
 * describes a fixed index event - but traded value, price and return all drift
 * from the day it was printed, and the ratio that actually decides whether a
 * name is tradeable is flow divided by *current* traded value. That is why a
 * six-week-old table stops being useful long before the rebalance happens.
 *
 * Everything here is arithmetic over candles. No network, no database, so the
 * behaviour that matters - what happens on a missing day, a zero volume, a
 * suspended stock - is testable directly rather than only in production.
 */

/**
 * A number, where absent is absent.
 *
 * Number(null) is 0, Number('') is 0, and Number.isFinite is true for both -
 * so the obvious guard reports a missing figure as a real zero. Here that
 * turns "we have no flow estimate for this name" into "this name has no
 * expected flow", which is a claim, and a wrong one. Zero itself has to keep
 * getting through, so it cannot be solved with a truthiness test either.
 */
function numeric(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Upstox candles are [timestamp, open, high, low, close, volume, open_interest]
 * and arrive newest-first. Nothing here assumes that order; sorting is cheap
 * and an upstream change to it would otherwise reverse every return silently.
 */
export function toDailyRows(candles) {
  const rows = [];
  for (const candle of candles || []) {
    if (!Array.isArray(candle) || candle.length < 6) continue;
    const [timestamp, , , , close, volume] = candle;
    const date = String(timestamp || '').slice(0, 10);
    const closeValue = Number(close);
    const volumeValue = Number(volume);
    // A candle without a usable close is not a trading day for our purposes.
    // Volume may legitimately be zero - a stock can be suspended or untraded -
    // and that is a real observation, so it is kept rather than dropped.
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
    if (!Number.isFinite(closeValue) || closeValue <= 0) continue;
    rows.push({
      date,
      close: closeValue,
      volume: Number.isFinite(volumeValue) && volumeValue >= 0 ? volumeValue : 0,
      // Traded value is approximated as close x volume, because the candle
      // does not carry turnover. The exchange's own figure uses VWAP, so this
      // runs a little off - which is why the source table's ADVT is stored
      // alongside rather than discarded: a large divergence between the two
      // means the instrument mapping is wrong, not that the maths drifted.
      value: closeValue * (Number.isFinite(volumeValue) && volumeValue > 0 ? volumeValue : 0),
    });
  }
  return rows.sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * Average daily traded value over the last N sessions, in the candle's own
 * currency.
 *
 * Sessions, not calendar days: a three-month window over an exchange with
 * holidays is about sixty trading days, and dividing by ninety would understate
 * every stock by a third.
 *
 * Returns null rather than zero when there is nothing to average. Zero would
 * flow into the days-of-ADVT divisor and read as infinite liquidity impact,
 * which is the opposite of what no data means.
 */
export function averageDailyValue(rows, sessions = 60) {
  const window = (rows || []).slice(-Math.max(1, sessions));
  if (!window.length) return null;
  const traded = window.filter((row) => row.value > 0);
  // Every session at zero volume is a suspended or unlisted name. Averaging to
  // zero would claim it trades nothing, which is true but useless as a divisor.
  if (!traded.length) return null;
  return traded.reduce((sum, row) => sum + row.value, 0) / traded.length;
}

/**
 * Simple return between the last close on or before `from` and the latest.
 *
 * On or before, not on: an announcement lands on a date the exchange may not
 * have traded, and requiring an exact match would return null for every event
 * announced on a weekend - which is most of them.
 */
export function returnSince(rows, fromDate) {
  const sorted = rows || [];
  if (sorted.length < 2 || !fromDate) return null;
  const cutoff = String(fromDate).slice(0, 10);

  let base = null;
  for (const row of sorted) {
    if (row.date <= cutoff) base = row;
    else break;
  }
  // No session at or before the date means the window does not reach back far
  // enough. Falling back to the earliest available row would quietly measure a
  // different period than the one being reported.
  if (!base || !(base.close > 0)) return null;

  const latest = sorted[sorted.length - 1];
  if (latest.date === base.date) return null;
  return (latest.close / base.close) - 1;
}

/**
 * How many sessions of normal volume the passive trade represents.
 *
 * Sign is preserved: an outflow is negative sessions, exactly as the source
 * tables print it. Taking the magnitude would rank a forced seller alongside a
 * forced buyer.
 */
export function daysOfAdvt(flowUsdMn, advtUsdMn) {
  const flow = numeric(flowUsdMn);
  const advt = numeric(advtUsdMn);
  if (flow === null || advt === null) return null;
  // Guarded rather than allowed to produce Infinity. A stock with no traded
  // value has an undefined ratio, and Infinity would sort to the top of a
  // "most impactful" list on the strength of having no data at all.
  if (advt <= 0) return null;
  return flow / advt;
}

/**
 * Convert a rupee figure to millions of dollars, so it is comparable with a
 * flow estimate that is published in dollars.
 *
 * Both sides must be one currency before they are divided. Dividing a dollar
 * flow by a rupee ADVT understates the ratio by about ninety times and makes
 * every name look effortlessly tradeable.
 */
export function inrToUsdMillions(valueInr, usdInr) {
  const value = numeric(valueInr);
  const rate = numeric(usdInr);
  if (value === null || rate === null || rate <= 0) return null;
  return value / rate / 1_000_000;
}

/**
 * Everything the refresh writes for one entry, or the reason it cannot.
 *
 * A reason rather than a silent null: an unpriced row must say whether it was
 * never mapped, returned no candles, or has no traded volume - those call for
 * three different fixes, and a blank cell distinguishes none of them.
 */
export function quoteFor({ candles, announcedOn, flowUsdMn, usdInr, sessions = 60 } = {}) {
  const rows = toDailyRows(candles);
  if (!rows.length) return { refresh_note: 'no candles returned for this instrument' };

  const advtInr = averageDailyValue(rows, sessions);
  const advtUsdMn = advtInr === null ? null : inrToUsdMillions(advtInr, usdInr);
  const latest = rows[rows.length - 1];

  return {
    last_price_inr: latest.close,
    advt_3m_usd_mn: advtUsdMn,
    usd_inr: numeric(usdInr) !== null && numeric(usdInr) > 0 ? numeric(usdInr) : null,
    days_of_advt: daysOfAdvt(flowUsdMn, advtUsdMn),
    return_since_announced_pct: (() => {
      const value = returnSince(rows, announcedOn);
      return value === null ? null : value * 100;
    })(),
    refresh_note: advtUsdMn === null
      ? 'priced, but no traded volume in the window'
      : null,
  };
}
