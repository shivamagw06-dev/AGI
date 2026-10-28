/**
 * Reading one manager's filings out of several CIKs.
 *
 * A manager's 13F reporting can move between legal entities. BlackRock's has
 * moved twice, so pointing the roster at the current entity - correct, because
 * the old one went silent - left it holding 11 quarters against its peers' 42,
 * with 69 more periods sitting under a CIK nothing looked at any more.
 *
 * Each CIK carries an explicit window on report_date. Declared, not inferred:
 * a "prefer the newest CIK" rule breaks in exactly the cases that matter,
 * because entities overlap while a transition completes and recency then
 * silently drops the filing that actually has the holdings in it.
 */

/**
 * Whether a period belongs to this CIK's window. Bounds are inclusive.
 *
 * A null bound is open, not absent. Reading a null effective_from as "no
 * filings qualify" would drop a predecessor's entire history, which is the one
 * thing this exists to recover - and it would do it silently, because an empty
 * result looks exactly like a filer that never filed.
 */
export function withinWindow(entry, reportDate) {
  const period = String(reportDate || '').slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(period)) return false;
  const from = entry?.effective_from ? String(entry.effective_from).slice(0, 10) : null;
  const to = entry?.effective_to ? String(entry.effective_to).slice(0, 10) : null;
  if (from && period < from) return false;
  if (to && period > to) return false;
  return true;
}

/**
 * The CIKs to scan, primary first.
 *
 * Primary first so the manager's own CIK is read even when a time ceiling cuts
 * the run short - the current book matters more than deep history, and a
 * truncated scan should lose the oldest quarters rather than the newest.
 */
export function scanOrder(primaryCik, extras = []) {
  const seen = new Set();
  const order = [];
  const push = (entry) => {
    const cik = String(entry?.cik || '').trim();
    if (!cik || seen.has(cik)) return;
    seen.add(cik);
    order.push({ ...entry, cik });
  };

  if (primaryCik) push({ cik: primaryCik, role: 'primary', effective_from: null, effective_to: null });
  for (const entry of extras || []) {
    if (String(entry?.role || '') === 'primary') push(entry);
  }
  for (const entry of extras || []) push(entry);
  return order;
}

/**
 * Merge filings gathered per CIK into one set, and report what was dropped.
 *
 * Two things are reported rather than swallowed:
 *
 * Filings outside every window. Usually correct - a predecessor kept filing
 * past its boundary, or the boundary is a quarter off - but always worth
 * knowing, because a wrong boundary silently truncates history and an empty
 * result is indistinguishable from a filer that never filed.
 *
 * Periods claimed by more than one CIK. With declared windows this should be
 * impossible, so if it happens the windows are wrong. The primary wins, so the
 * outcome is at least deterministic, and the conflict is named so the boundary
 * can be corrected.
 */
export function mergeByWindow(collected = []) {
  const kept = [];
  const outside = [];
  const byPeriod = new Map();
  const conflicts = [];

  for (const group of collected || []) {
    const entry = group?.entry || {};
    for (const filing of group?.filings || []) {
      if (!withinWindow(entry, filing?.report_date)) {
        outside.push({ cik: entry.cik, accession_number: filing?.accession_number, report_date: filing?.report_date });
        continue;
      }
      const period = String(filing.report_date).slice(0, 10);
      const owner = byPeriod.get(period);
      if (owner && owner !== entry.cik) {
        conflicts.push({ report_date: period, kept: owner, dropped: entry.cik });
        // The primary already claimed it, or an earlier CIK in scan order did.
        // Either way one owner per period, decided the same way every run.
        continue;
      }
      if (!owner) byPeriod.set(period, entry.cik);
      kept.push(filing);
    }
  }

  // Deduplicate by accession: a filing can appear in both a recent block and
  // an archive file, and ingesting it twice would delete and rewrite the same
  // holdings for no reason.
  const seen = new Set();
  const filings = kept.filter((filing) => {
    const key = String(filing?.accession_number || '');
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return { filings, outside, conflicts };
}
