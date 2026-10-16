/**
 * Whether two identifier mappings can hold the same ticker.
 *
 * security_identifier_history is keyed (cusip, valid_from) and carries a
 * valid_to, and the resolver picks the mapping valid at a given date. So one
 * ticker belonging to two CUSIPs is not automatically wrong - it is how a
 * ticker moving from an old CUSIP to a new one after a corporate action is
 * represented, each owning it for the stretch it actually described.
 *
 * What is wrong is two CUSIPs claiming one ticker over the same dates. That
 * is the difference between a succession and a collision, and the dates are
 * the only thing that tells them apart:
 *
 *   Carnival Corp (143658300) and Carnival plc (G2004J103) trade at the same
 *   time as CCL and CUK. Their windows overlap, so giving CCL to both would
 *   put one company's price on the other's position.
 *
 *   An issuer that re-registers after a spin-off leaves the old CUSIP behind
 *   on the date the new one starts. The windows touch but do not overlap, and
 *   the ticker legitimately belongs to each in its own period.
 *
 * An open-ended window (valid_to null) runs to the end of time, which is why
 * a proposal must bound its own window rather than claiming forever.
 *
 * valid_to is exclusive - the resolver reads a mapping as applying while
 * valid_to has not been reached - and the table checks valid_to > valid_from.
 * Both push the same way: a window that ends on the last date the security
 * was held is wrong, because it stops one day before that date is covered,
 * and for a security held in a single quarter it is not a window at all.
 */

const START = '0000-01-01';
const END = '9999-12-31';

/** Do two [from, to] windows share any day? */
export function windowsOverlap(a, b) {
  const aFrom = a?.from || START;
  const aTo = a?.to || END;
  const bFrom = b?.from || START;
  const bTo = b?.to || END;
  // Ends are exclusive, so a window ending exactly where another begins is a
  // handover, not a clash - which is the shape a succession actually takes.
  return aFrom < bTo && bFrom < aTo;
}

/**
 * The CUSIP already holding this ticker over the proposed window, if any.
 *
 * `owners` is the list of existing mappings for that ticker, each with its
 * own cusip and window. A mapping belonging to the same CUSIP is not a
 * conflict with itself.
 */
export function conflictingOwner(owners, cusip, window) {
  for (const owner of owners || []) {
    if (!owner?.cusip || owner.cusip === cusip) continue;
    if (windowsOverlap(window, { from: owner.valid_from, to: owner.valid_to })) return owner;
  }
  return null;
}

/**
 * The window a recovered mapping should claim.
 *
 * It runs from the first date the security is held to the last, and stays
 * open only when the position is still current - a security that stopped
 * being reported has stopped, and claiming its ticker forever would block
 * the successor that took the symbol over.
 */
export function proposedWindow({ earliest, latest }, latestReportDate) {
  const stillHeld = latest && latestReportDate && latest >= latestReportDate;
  return {
    from: earliest || null,
    // The day after the last report date it was held. An exclusive end set to
    // that date itself would not cover it, and would equal valid_from for a
    // security held in one quarter - which the table rejects outright.
    to: stillHeld ? null : dayAfter(latest),
  };
}

function dayAfter(date) {
  if (!date) return null;
  const d = new Date(`${String(date).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}
