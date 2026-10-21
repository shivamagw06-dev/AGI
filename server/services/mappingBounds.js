/**
 * Bounding a mapping that claims a ticker from 1900.
 *
 * Mappings written by the early identifier backfill start at 1900-01-01. The
 * vendor was answering what a CUSIP maps to now, and storing that as valid
 * from 1900 asserts that today's ticker applied to every filing ever made -
 * which identifierBackfill.js already says in as many words.
 *
 * It is not only wrong in the abstract. An unbounded start claims the ticker
 * for all time, so no succession can take it afterwards: ten venue-ticker
 * recoveries covering $279bn are refused because an incumbent holds their
 * symbol from 1900 to open. The window check added for exactly this case
 * cannot help while one side of the comparison is infinite.
 *
 * The evidence for a real start is the first date the security is held. A
 * mapping cannot have described a holding that did not exist, and the resolver
 * reads mappings as at a report date, so a start on the first observed
 * quarter covers every date that will ever be asked of it.
 */

/** The first date each CUSIP is observed in holdings. */
export function firstSeenByCusip(holdings) {
  const first = new Map();
  for (const row of holdings || []) {
    const cusip = String(row?.cusip || '').trim().toUpperCase();
    const date = row?.report_date;
    if (!cusip || !date) continue;
    const seen = first.get(cusip);
    if (!seen || date < seen) first.set(cusip, date);
  }
  return first;
}

/** Mappings whose start is a placeholder rather than an observation. */
export function isUnbounded(mapping, { placeholder = '1900-01-01' } = {}) {
  const from = String(mapping?.valid_from || '').slice(0, 10);
  return !from || from <= placeholder;
}

/**
 * The corrected start for a mapping, or why it cannot be corrected.
 *
 * A mapping for a CUSIP that appears in no holding is left alone. There is no
 * evidence to bound it with, and inventing one would be the same fault in the
 * other direction - a narrower claim that is equally unsupported.
 */
export function boundedStart(mapping, firstSeen) {
  if (!isUnbounded(mapping)) return { from: null, reason: 'already bounded' };
  const cusip = String(mapping?.cusip || '').trim().toUpperCase();
  const seen = firstSeen?.get?.(cusip);
  if (!seen) return { from: null, reason: 'never observed in holdings' };
  // Nothing to do if the placeholder happens to equal the evidence.
  if (String(mapping.valid_from || '').slice(0, 10) === seen) return { from: null, reason: 'already correct' };
  return { from: seen, reason: null };
}

/**
 * Rows to write, given the mappings and what the holdings show.
 *
 * valid_from is part of the table's key, so moving it is an insert of the
 * corrected row and a delete of the placeholder - not an update. The caller
 * does both, in that order, so a failure between them leaves the security
 * mapped twice rather than not at all.
 */
export function planBounds(mappings, firstSeen) {
  const plan = [];
  const skipped = { alreadyBounded: 0, neverObserved: 0, alreadyCorrect: 0 };
  for (const mapping of mappings || []) {
    const { from, reason } = boundedStart(mapping, firstSeen);
    if (!from) {
      if (reason === 'already bounded') skipped.alreadyBounded += 1;
      else if (reason === 'never observed in holdings') skipped.neverObserved += 1;
      else skipped.alreadyCorrect += 1;
      continue;
    }
    plan.push({ mapping, from, was: String(mapping.valid_from || '').slice(0, 10) });
  }
  return { plan, skipped };
}
