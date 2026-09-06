/**
 * Which identifiers applied to a security on a given date.
 *
 * Resolution used to take the newest mapping for a CUSIP regardless of when the
 * filing was made:
 *
 *   .order('valid_from', { ascending: false })   // then keep the first
 *
 * A CUSIP is not permanently stable. It is reassigned after corporate actions,
 * and an issuer carries several across share classes and depositary lines. So
 * a mapping created in 2025 was being applied to a holding disclosed in 2023,
 * relabelling it as whatever that CUSIP means now.
 *
 * The rule here is the one a filing deserves: use the mapping that was in force
 * on the report date, and if none was, leave the holding unmapped. An unmapped
 * position is visibly incomplete. A confidently mislabelled one is not, and it
 * propagates into consensus, sector weights and any price fetched against it.
 */

/** Normalised for comparison; a CUSIP is nine characters, case-insensitive. */
export function cleanIdentifier(value) {
  return String(value || '').trim().toUpperCase() || null;
}

/**
 * Pick the mapping in force on `asOf` from a security's history.
 *
 * `rows` are that CUSIP's mappings in any order. A row applies when it started
 * on or before the date and has not ended by it; valid_to is exclusive, so a
 * mapping ending on the report date has already stopped applying.
 *
 * When several qualify - overlapping intervals from different sources - the
 * one that started latest wins, then a manually verified row over an
 * automatic one. Manual verification is somebody having checked, and that
 * should outrank a vendor's guess.
 */
export function mappingAsOf(rows, asOf) {
  const date = String(asOf || '').slice(0, 10);
  if (!date) return null;

  const applicable = (rows || []).filter((row) => {
    const from = String(row?.valid_from || '').slice(0, 10);
    const to = row?.valid_to ? String(row.valid_to).slice(0, 10) : null;
    if (!from || from > date) return false;
    return !to || to > date;
  });
  if (!applicable.length) return null;

  applicable.sort((a, b) => {
    const from = String(b.valid_from || '').localeCompare(String(a.valid_from || ''));
    if (from !== 0) return from;
    return Number(Boolean(b.manually_verified)) - Number(Boolean(a.manually_verified));
  });
  return applicable[0];
}

/**
 * The canonical key for a security at a date.
 *
 * Falls back to the CUSIP itself, which is the bootstrap identity: a security
 * is its own key until a mapping merges it with another. Returning the CUSIP
 * rather than null means aggregation still groups something sensible for a
 * security nobody has mapped yet.
 */
export function securityKeyAsOf(rows, asOf, cusip) {
  const mapping = mappingAsOf(rows, asOf);
  return cleanIdentifier(mapping?.security_key) || cleanIdentifier(cusip);
}

/**
 * Group history rows by CUSIP so a caller can resolve many at once without a
 * query per holding.
 */
export function indexHistory(rows) {
  const byCusip = new Map();
  for (const row of rows || []) {
    const cusip = cleanIdentifier(row?.cusip);
    if (!cusip) continue;
    if (!byCusip.has(cusip)) byCusip.set(cusip, []);
    byCusip.get(cusip).push(row);
  }
  return byCusip;
}

/**
 * Resolve a set of CUSIPs as at one date.
 *
 * Returns a Map from CUSIP to { ticker, issuer_name, security_key } - the
 * fields a holding row may carry, and no more, because callers spread this
 * straight onto a row and provenance columns would break the insert. A CUSIP
 * absent from the result has no mapping for that date and must stay unmapped
 * rather than borrowing one from another period.
 */
export function resolveAsOf(historyRows, cusips, asOf) {
  const byCusip = indexHistory(historyRows);
  const out = new Map();
  for (const raw of cusips || []) {
    const cusip = cleanIdentifier(raw);
    if (!cusip) continue;
    const mapping = mappingAsOf(byCusip.get(cusip) || [], asOf);
    if (!mapping) continue;
    out.set(cusip, {
      ticker: mapping.ticker || null,
      issuer_name: mapping.issuer_name || null,
      security_key: cleanIdentifier(mapping.security_key) || cusip,
    });
  }
  return out;
}
