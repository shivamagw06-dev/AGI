/**
 * Bid-ask spread in basis points, shared by every market feed.
 *
 * The Upstox feed computed this inline without checking that the book was
 * uncrossed, so whenever the depth snapshot arrived with ask below bid - stale
 * one-sided quotes around the open and close, or a missing side - it produced a
 * negative spread. On 2026-08-19 that was 624 of 1,698 stored signals, 37%,
 * bottoming at -599.99 basis points.
 *
 * A negative spread is not a small number, it is an impossible one, and it
 * flowed into the liquidity gate: `spreadBps <= maximumSpreadBps` passes
 * trivially for any negative value, so the widest, least tradeable books were
 * the ones most likely to clear the filter.
 *
 * The Groww feed already guarded this. Both now share one implementation, so
 * the two providers cannot disagree about what a spread is.
 */

/** Finite, strictly positive number, or null. Prices of 0 are not prices. */
function positivePrice(value) {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

/**
 * @returns {number|null} spread in bps, or null when it cannot be measured.
 *   Null means "unknown", never "zero" - a caller must not read a missing
 *   spread as a tight one.
 */
export function normalizeSpreadBps(bid, ask) {
  const normalizedBid = positivePrice(bid);
  const normalizedAsk = positivePrice(ask);
  if (normalizedBid === null || normalizedAsk === null) return null;
  // Crossed or locked-inverted book: the snapshot is stale or one-sided, so the
  // spread is unknown rather than negative.
  if (normalizedAsk < normalizedBid) return null;
  const mid = (normalizedAsk + normalizedBid) / 2;
  if (!(mid > 0)) return null;
  return Number((((normalizedAsk - normalizedBid) / mid) * 10_000).toFixed(4));
}

/**
 * Does this book pass a maximum-spread liquidity gate?
 *
 * `ok` keeps the existing permissive rule: a name whose spread cannot be
 * measured still passes, because roughly a quarter of the universe has no
 * usable quote at any given moment and failing them closed would empty the
 * board rather than improve it.
 *
 * `verified` is the part that was missing. Unknown liquidity is not evidence
 * of good liquidity, and until now the two were indistinguishable downstream -
 * every row reported `liquidity_ok: true` whether its spread had been measured
 * at 4bps or never measured at all.
 *
 * @returns {{ok: boolean, verified: boolean, reason: string}}
 */
export function spreadWithinLimit(spreadBps, maximumSpreadBps) {
  if (spreadBps === null || spreadBps === undefined) {
    return { ok: true, verified: false, reason: 'spread_unknown' };
  }
  if (!Number.isFinite(spreadBps) || spreadBps < 0) {
    // Reachable only from stored history written before the crossed-book guard.
    return { ok: true, verified: false, reason: 'spread_invalid' };
  }
  return spreadBps <= maximumSpreadBps
    ? { ok: true, verified: true, reason: 'within_limit' }
    : { ok: false, verified: true, reason: 'spread_too_wide' };
}
